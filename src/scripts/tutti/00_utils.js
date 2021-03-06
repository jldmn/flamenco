(function ( $ ) {
    $.fn.flashOnce = function() {
        var target = this;
        this
            .addClass('flash-on')
            .delay(1000) // this delay is linked to the transition in the flash-on CSS class.
            .queue(function() {
                target
                    .removeClass('flash-on')
                    .addClass('flash-off')
                    .dequeue()
                ;})
            .delay(1000)  // this delay is just to clean up the flash-X classes.
            .queue(function() {
                target
                    .removeClass('flash-on flash-off')
                    .dequeue()
                ;})
        ;
        return this;
    };

    /**
     * Fades out the element, then erases its contents and shows the now-empty element again.
     */
    $.fn.fadeOutAndClear = function(fade_speed) {
        var target = this;
        this
            .fadeOut(fade_speed, function() {
                target
                    .html('')
                    .show();
            });
    }

    $.fn.hideAndRemove = function(hide_speed, finished) {
        this.slideUp(hide_speed, function() {
            this.remove();
            if (typeof finished !== 'undefined') finished();
        });
    }

    $.fn.removeClassPrefix = function(prefix) {
        this.each(function(i, el) {
            var classes = el.className.split(" ").filter(function(c) {
                return c.lastIndexOf(prefix, 0) !== 0;
            });
            el.className = $.trim(classes.join(" "));
        });
        return this;
    }

    /*
     * jQuery autoResize (textarea auto-resizer)
     * @copyright James Padolsey http://james.padolsey.com
     * @version 1.04
     * cracked by icyleaf <icyleaf.cn@gmail.com>
     * https://gist.github.com/icyleaf/269160
     */
    $.fn.autoResize = function(options) {
        var settings = $.extend({
            onResize : function(){},
            animate : true,
            animateDuration : 0,
            animateCallback : function(){},
            extraSpace : 20,
            limit: 500
        }, options);

        this.filter('textarea').each(function(){
            var textarea = $(this).css({resize:'none','overflow-y':'hidden'}),
            origHeight = textarea.height(),
            clone = (function(){
                var props = ['height','width','lineHeight','textDecoration','letterSpacing'],
                    propOb = {};

                $.each(props, function(i, prop){
                    propOb[prop] = textarea.css(prop);
                });

                return textarea.clone().removeAttr('id').removeAttr('name').css({
                    position: 'absolute',
                    top: 0,
                    left: -9999
                }).css(propOb).attr('tabIndex','-1').insertBefore(textarea);
            })(),
            lastScrollTop = null,
            updateSize = function() {

                clone.height(0).val($(this).val()).scrollTop(10000);
                var scrollTop = Math.max(clone.scrollTop(), origHeight) + settings.extraSpace,
                    toChange = $(this).add(clone);

                if (lastScrollTop === scrollTop) { return; }
                lastScrollTop = scrollTop;

                if ( scrollTop >= settings.limit ) {
                    if ( settings.limit != 0) {
                        $(this).css('overflow-y','').css('height', settings.limit+'px');
                        return;
                    }
                }
                settings.onResize.call(this);
                settings.animate && textarea.css('display') === 'block' ?
                    toChange.stop().animate({height:scrollTop}, settings.animateDuration, settings.animateCallback)
                    : toChange.height(scrollTop);
            };
            textarea
                .unbind('.dynSiz')
                .bind('keyup.dynSiz', updateSize)
                .bind('keydown.dynSiz', updateSize)
                .bind('change.dynSiz', updateSize)
                .bind('blur.dynSiz', updateSize);
        });
        return this;
    };

}(jQuery));

function clearMainOverlay(){
    $('#col_main-overlay-content').html('');
    $('#col_main-overlay').removeAttr('class');
}

$(document).ready(function() {
    /* Clear the modal inner html when hidding */
    $('#modal').on('hidden.bs.modal', function () {
        $("#modal .modal-body").html('');
    });
});

document.onkeydown = function(evt) {
    evt = evt || window.event;
    if (evt.keyCode == 27 || evt.key == 'Escape') {
        if ($('#col_main-overlay').hasClass('active')){
            /* If we're in the context of a job, it means we're closing Task details*/
            if (ProjectUtils.context() == 'job') {
                closeTaskDetails(); // From view_task_embed template
            }
        }
    }
};

/* Returns a more-or-less reasonable message given an error response object. */
function xhrErrorResponseMessage(err) {
    if (typeof err.responseJSON == 'undefined')
        return err.statusText;

    if (typeof err.responseJSON._error != 'undefined' && typeof err.responseJSON._error.message != 'undefined')
        return err.responseJSON._error.message;

    if (typeof err.responseJSON._message != 'undefined')
        return err.responseJSON._message

    return err.statusText;
}

function xhrErrorResponseElement(err, prefix) {
    msg = xhrErrorResponseMessage(err);
    return $('<span>')
        .text(prefix + msg);
}
