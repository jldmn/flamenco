import os

# Enable reads (GET), inserts (POST) and for resources/collections
# (if you omit this line, the API will default to ['GET'] and provide
# read-only access to the endpoint).
RESOURCE_METHODS = ['GET', 'POST']

# Enable reads (GET), edits (PATCH), replacements (PUT) and deletes of
# individual items  (defaults to read-only item access).
ITEM_METHODS = ['GET', 'PUT', 'DELETE', 'PATCH']

_file_embedded_schema = {
    'type': 'objectid',
    'data_relation': {
        'resource': 'files',
        'field': '_id',
        'embeddable': True
    }
}

_required_user_embedded_schema = {
    'type': 'objectid',
    'required': True,
    'data_relation': {
        'resource': 'users',
        'field': '_id',
        'embeddable': True
    },
}

_activity_object_type = {
    'type': 'string',
    'required': True,
    'allowed': [
        'project',
        'user',
        'job',
        'task'
    ],
}

_permissions_embedded_schema = {
    'groups': {
        'type': 'list',
        'schema': {
            'type': 'dict',
            'schema': {
                'group': {
                    'type': 'objectid',
                    'required': True,
                    'data_relation': {
                        'resource': 'groups',
                        'field': '_id',
                        'embeddable': True
                    }
                },
                'methods': {
                    'type': 'list',
                    'required': True,
                    'allowed': ['GET', 'PUT', 'POST', 'DELETE']
                }
            }
        },
    },
    'users': {
        'type': 'list',
        'schema': {
            'type': 'dict',
            'schema': {
                'user' : {
                    'type': 'objectid',
                    'required': True,
                },
                'methods': {
                    'type': 'list',
                    'required': True,
                    'allowed': ['GET', 'PUT', 'POST', 'DELETE']
                }
            }
        }
    },
    'world': {
        'type': 'list',
        #'required': True,
        'allowed': ['GET',]
    },
    'is_free': {
        'type': 'boolean',
    }
}

users_schema = {
    'full_name': {
        'type': 'string',
        'minlength': 3,
        'maxlength': 128,
        'required': True,
    },
    'username': {
        'type': 'string',
        'minlength': 3,
        'maxlength': 128,
        'required': True,
        'unique': True,
    },
    'email': {
        'type': 'string',
        'minlength': 5,
        'maxlength': 60,
    },
    'roles': {
        'type': 'list',
        'allowed': ["admin", "subscriber", "demo"],
    },
    'groups': {
        'type': 'list',
        'default': [],
        'schema': {
            'type': 'objectid',
            'data_relation': {
                'resource': 'groups',
                'field': '_id',
                'embeddable': True
            }
        }
    },
    'auth': {
        # Storage of authentication credentials (one will be able to auth with
        # multiple providers on the same account)
        'type': 'list',
        'required': True,
        'schema': {
            'type': 'dict',
            'schema': {
                'provider': {
                    'type': 'string',
                    'allowed': ["blender-id", "local"],
                },
                'user_id': {
                    'type': 'string'
                },
                # A token is considered a "password" in case the provider is
                # "local".
                'token': {
                    'type': 'string'
                }
            }
        }
    },
    'settings': {
        'type': 'dict',
        'schema': {
            'email_communications': {
                'type': 'integer',
                'allowed': [0, 1]
            }
        }
    }
}

tokens_schema = {
    'user': {
        'type': 'objectid',
        'required': True,
    },
    'token': {
        'type': 'string',
        'required': True,
    },
    'expire_time': {
        'type': 'datetime',
        'required': True,
    },
    'is_subclient_token': {
        'type': 'boolean',
        'required': False,
    }
}

files_schema = {
    'name': {
        'type': 'string',
        'required': True,
    },
    'description': {
        'type': 'string',
    },
    'content_type': { # MIME type image/png video/mp4
        'type': 'string',
        'required': True,
    },
    # Duration in seconds, only if it's a video
    'duration': {
        'type': 'integer',
    },
    'size': { # xs, s, b, 720p, 2K
        'type': 'string'
    },
    'format': { # human readable format, like mp4, HLS, webm, mov
        'type': 'string'
    },
    'width': { # valid for images and video content_type
        'type': 'integer'
    },
    'height': {
        'type': 'integer'
    },
    'user': {
        'type': 'objectid',
        'required': True,
    },
    'length': { # Size in bytes
        'type': 'integer',
        'required': True,
    },
    'md5': {
        'type': 'string',
        'required': True,
    },
    'filename': {
        'type': 'string',
        'required': True,
    },
    'backend': {
        'type': 'string',
        'required': True,
        'allowed': ["attract-web", "pillar", "cdnsun", "gcs", "unittest"]
    },
    'file_path': {
        'type': 'string',
        #'required': True,
        'unique': True,
    },
    'link': {
        'type': 'string',
    },
    'link_expires': {
        'type': 'datetime',
    },
    'project': {
        # The project node the files belongs to (does not matter if it is
        # attached to an asset or something else). We use the project id as
        # top level filtering, folder or bucket name. Later on we will be able
        # to join permissions from the project and verify user access.
        'type': 'objectid',
        'data_relation': {
            'resource': 'projects',
            'field': '_id',
            'embeddable': True
        },
    },
    'variations': { # File variations (used to be children, see above)
        'type': 'list',
        'schema': {
            'type': 'dict',
            'schema': {
                'is_public': { # If True, the link will not be hashed or signed
                    'type': 'boolean'
                },
                'content_type': { # MIME type image/png video/mp4
                    'type': 'string',
                    'required': True,
                },
                'duration': {
                    'type': 'integer',
                },
                'size': { # xs, s, b, 720p, 2K
                    'type': 'string'
                },
                'format': { # human readable format, like mp4, HLS, webm, mov
                    'type': 'string'
                },
                'width': { # valid for images and video content_type
                    'type': 'integer'
                },
                'height': {
                    'type': 'integer'
                },
                'length': { # Size in bytes
                    'type': 'integer',
                    'required': True,
                },
                'md5': {
                    'type': 'string',
                    'required': True,
                },
                'file_path': {
                    'type': 'string',
                },
                'link': {
                    'type': 'string',
                }
            }
        }
    },
    'processing': {
        'type': 'dict',
        'schema': {
            'job_id': {
                'type': 'string' # can be int, depending on the backend
            },
            'backend': {
                'type': 'string',
                'allowed': ["zencoder", "local"]
            },
            'status': {
                'type': 'string',
                'allowed': ["pending", "waiting", "processing", "finished",
                    "failed", "cancelled"]
            },
        }
    }
}

groups_schema = {
    'name': {
        'type': 'string',
        'required': True
    }
}

projects_schema = {
    'name': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 128,
        'required': True,
    },
    'description': {
        'type': 'string',
    },
    # Logo
    'picture_square': _file_embedded_schema,
    # Header
    'picture_header': _file_embedded_schema,
    'user': {
        'type': 'objectid',
        'required': True,
        'data_relation': {
            'resource': 'users',
            'field': '_id',
            'embeddable': True
        },
    },
    'url': {
        'type': 'string'
    },
    'organization': {
        'type': 'objectid',
        'nullable': True,
        'data_relation': {
           'resource': 'organizations',
           'field': '_id',
           'embeddable': True
        },
    },
    'status': {
        'type': 'string',
        'allowed': [
            'active',
            'archived',
        ],
    },
    'permissions': {
        'type': 'dict',
        'schema': _permissions_embedded_schema
    }
}

activities_subscriptions_schema = {
    'user': _required_user_embedded_schema,
    'context_object_type': _activity_object_type,
    'context_object': {
        'type': 'objectid',
        'required': True
    },
    'notifications': {
        'type': 'dict',
        'schema': {
            'email': {
                'type': 'boolean',
            },
            'web': {
                'type': 'boolean',
                'default': True
            },
        }
    },
    'is_subscribed': {
        'type': 'boolean',
        'default': True
    }
}

activities_schema = {
    'actor_user': _required_user_embedded_schema,
    'verb': {
        'type': 'string',
        'required': True
    },
    'object_type': _activity_object_type,
    'object': {
        'type': 'objectid',
        'required': True
    },
    'context_object_type': _activity_object_type,
    'context_object': {
        'type': 'objectid',
        'required': True
    },
}

notifications_schema = {
    'user': _required_user_embedded_schema,
    'activity': {
        'type': 'objectid',
        'required': True,
    },
    'is_read': {
        'type': 'boolean',
    },
}

jobs_schema = {
    'name': {
        'type': 'string',
        'required': True
    }
}

users = {
    'item_title': 'user',

    # We choose to override global cache-control directives for this resource.
    'cache_control': 'max-age=10,must-revalidate',
    'cache_expires': 10,

    'resource_methods': ['GET'],
    'item_methods': ['GET', 'PUT'],
    'public_item_methods': ['GET'],

    # By default don't include the 'auth' field. It can still be obtained
    # using projections, though, so we block that in hooks.
    'datasource': {'projection': {u'auth': 0}},

    'schema': users_schema
}

tokens = {
    'resource_methods': ['GET', 'POST'],

    # Allow 'token' to be returned with POST responses
    #'extra_response_fields': ['token'],

    'schema' : tokens_schema
}

files = {
    'resource_methods': ['GET', 'POST'],
    'public_methods': ['GET'],
    'public_item_methods': ['GET'],
    'schema': files_schema
}

groups = {
    'resource_methods': ['GET', 'POST'],
    'public_methods': ['GET'],
    'public_item_methods': ['GET'],
    'schema': groups_schema,
}

projects = {
    'schema': projects_schema,
    'public_item_methods': ['GET'],
    'public_methods': ['GET'],
    'soft_delete': True,
}

activities = {
    'schema': activities_schema,
}

activities_subscriptions = {
    'schema': activities_subscriptions_schema,
}

notifications = {
    'schema': notifications_schema,
}

jobs = {
    'schema': jobs_schema,
}

DOMAIN = {
    'users': users,
    'tokens': tokens,
    'files': files,
    'groups': groups,
    'projects': projects,
    'activities': activities,
    'activities-subscriptions': activities_subscriptions,
    'notifications': notifications,
    'jobs': jobs
}


MONGO_HOST = os.environ.get('MONGO_HOST', 'localhost')
MONGO_PORT = os.environ.get('MONGO_PORT', 27017)
MONGO_DBNAME = os.environ.get('MONGO_DBNAME', 'eve_flamenco')
CACHE_EXPIRES = 60
HATEOAS = False
UPSET_ON_PUT = False  # do not create new document on PUT of non-existant URL.
