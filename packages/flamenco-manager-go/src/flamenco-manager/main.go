package main

import (
	"flag"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"gopkg.in/mgo.v2"
	"gopkg.in/mgo.v2/bson"

	log "github.com/Sirupsen/logrus"
	auth "github.com/abbot/go-http-auth"

	"flamenco-manager/flamenco"

	"github.com/gorilla/mux"
)

const FLAMENCO_VERSION = "2.0-beta5"

// MongoDB session
var session *mgo.Session
var config flamenco.Conf
var upstream *flamenco.UpstreamConnection
var task_scheduler *flamenco.TaskScheduler
var task_update_pusher *flamenco.TaskUpdatePusher
var task_timeout_checker *flamenco.TaskTimeoutChecker

func http_status(w http.ResponseWriter, r *http.Request) {
	flamenco.SendStatusReport(w, r, session)
}

func http_register_worker(w http.ResponseWriter, r *http.Request) {
	mongo_sess := session.Copy()
	defer mongo_sess.Close()
	flamenco.RegisterWorker(w, r, mongo_sess.DB(""))
}

func http_schedule_task(w http.ResponseWriter, r *auth.AuthenticatedRequest) {
	task_scheduler.ScheduleTask(w, r)
}

func http_kick(w http.ResponseWriter, r *http.Request) {
	upstream.KickDownloader(false)
	fmt.Fprintln(w, "Kicked task downloader")
}

func http_task_update(w http.ResponseWriter, r *auth.AuthenticatedRequest) {
	mongo_sess := session.Copy()
	defer mongo_sess.Close()

	vars := mux.Vars(&r.Request)
	task_id := vars["task-id"]

	if !bson.IsObjectIdHex(task_id) {
		w.WriteHeader(http.StatusNotFound)
		fmt.Fprintf(w, "Invalid ObjectID passed as task ID: %s\n", task_id)
		return
	}

	flamenco.QueueTaskUpdateFromWorker(w, r, mongo_sess.DB(""), bson.ObjectIdHex(task_id))
}

/**
 * Called by a worker, to check whether it is allowed to keep running this task.
 */
func http_worker_may_run_task(w http.ResponseWriter, r *auth.AuthenticatedRequest) {
	mongo_sess := session.Copy()
	defer mongo_sess.Close()

	vars := mux.Vars(&r.Request)
	task_id := vars["task-id"]

	if !bson.IsObjectIdHex(task_id) {
		w.WriteHeader(http.StatusNotFound)
		fmt.Fprintf(w, "Invalid ObjectID passed as task ID: %s\n", task_id)
		return
	}

	flamenco.WorkerMayRunTask(w, r, mongo_sess.DB(""), bson.ObjectIdHex(task_id))
}

func http_worker_sign_off(w http.ResponseWriter, r *auth.AuthenticatedRequest) {
	mongo_sess := session.Copy()
	defer mongo_sess.Close()

	flamenco.WorkerSignOff(w, r, mongo_sess.DB(""))
}

func worker_secret(user, realm string) string {
	mongo_sess := session.Copy()
	defer mongo_sess.Close()

	return flamenco.WorkerSecret(user, mongo_sess.DB(""))
}

func shutdown(signum os.Signal) {
	// Always shut down after 2 seconds.
	timeout := flamenco.TimeoutAfter(2 * time.Second)

	go func() {
		log.Infof("Signal '%s' received, shutting down.", signum)
		task_timeout_checker.Close()
		task_update_pusher.Close()
		upstream.Close()
		session.Close()
		log.Warning("Shutdown complete, stopping process.")
		timeout <- false
	}()

	if <-timeout {
		log.Warning("Shutdown forced, stopping process.")
	}
	os.Exit(-2)
}

var cliArgs struct {
	verbose    bool
	debug      bool
	jsonLog    bool
	cleanSlate bool
}

func parseCliArgs() {
	flag.BoolVar(&cliArgs.verbose, "verbose", false, "Enable info-level logging")
	flag.BoolVar(&cliArgs.debug, "debug", false, "Enable debug-level logging")
	flag.BoolVar(&cliArgs.jsonLog, "json", false, "Log in JSON format")
	flag.BoolVar(&cliArgs.cleanSlate, "cleanslate", false, "Start with a clean slate; erases all tasks from the local MongoDB")
	flag.Parse()
}

func configLogging() {
	if cliArgs.jsonLog {
		log.SetFormatter(&log.JSONFormatter{})
	} else {
		log.SetFormatter(&log.TextFormatter{
			FullTimestamp: true,
		})
	}

	// Only log the warning severity or above.
	level := log.WarnLevel
	if cliArgs.debug {
		level = log.DebugLevel
	} else if cliArgs.verbose {
		level = log.InfoLevel
	}
	log.SetLevel(level)
}

func main() {
	parseCliArgs()
	configLogging()
	log.Infof("Starting Flamenco Manager version %s", FLAMENCO_VERSION)

	defer func() {
		// If there was a panic, make sure we log it before quitting.
		if r := recover(); r != nil {
			log.Panic(r)
		}
	}()

	config = flamenco.GetConf()
	has_tls := config.TLSCert != "" && config.TLSKey != ""
	if has_tls {
		config.OwnUrl = strings.Replace(config.OwnUrl, "http://", "https://", 1)
	} else {
		config.OwnUrl = strings.Replace(config.OwnUrl, "https://", "http://", 1)
		log.Warning("WARNING: TLS not enabled!")
	}

	log.Info("MongoDB database server :", config.DatabaseUrl)
	log.Info("Upstream Flamenco server:", config.Flamenco)
	log.Info("My URL is               :", config.OwnUrl)
	log.Info("Listening at            :", config.Listen)

	session = flamenco.MongoSession(&config)

	if cliArgs.cleanSlate {
		flamenco.CleanSlate(session.DB(""))
		log.Warning("Shutting down after performing clean slate")
		return
	}

	upstream = flamenco.ConnectUpstream(&config, session)
	task_scheduler = flamenco.CreateTaskScheduler(&config, upstream, session)
	task_update_pusher = flamenco.CreateTaskUpdatePusher(&config, upstream, session)
	task_timeout_checker = flamenco.CreateTaskTimeoutChecker(&config, session)

	// Set up our own HTTP server
	worker_authenticator := auth.NewBasicAuthenticator("Flamenco Manager", worker_secret)
	router := mux.NewRouter().StrictSlash(true)
	router.HandleFunc("/", http_status).Methods("GET")
	router.HandleFunc("/register-worker", http_register_worker).Methods("POST")
	router.HandleFunc("/task", worker_authenticator.Wrap(http_schedule_task)).Methods("POST")
	router.HandleFunc("/tasks/{task-id}/update", worker_authenticator.Wrap(http_task_update)).Methods("POST")
	router.HandleFunc("/may-i-run/{task-id}", worker_authenticator.Wrap(http_worker_may_run_task)).Methods("GET")
	router.HandleFunc("/sign-off", worker_authenticator.Wrap(http_worker_sign_off)).Methods("POST")
	router.HandleFunc("/kick", http_kick)

	upstream.SendStartupNotification()
	go task_update_pusher.Go()
	go task_timeout_checker.Go()

	// Handle Ctrl+C
	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt)
	signal.Notify(c, syscall.SIGTERM)
	go func() {
		for signum := range c {
			// Run the shutdown sequence in a goroutine, so that multiple Ctrl+C presses can be handled in parallel.
			go shutdown(signum)
		}
	}()

	// Fall back to insecure server if TLS certificate/key is not defined.
	if !has_tls {
		log.Fatal(http.ListenAndServe(config.Listen, router))
	} else {
		log.Fatal(http.ListenAndServeTLS(
			config.Listen,
			config.TLSCert,
			config.TLSKey,
			router))
	}
}
