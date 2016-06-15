![Sloop](/docs/img/splash.jpg?raw=true "Sloop")


Sloop is the fastest & most reliable RESTful push notification service so far. This package contains some tools that will ease the implementation of sloop into django projects.

# Django-Sloop

## Installation

1 - Install the package via Github or PIP

2 - Add **sloop** to the INSTALLED_APPS list in the settings file.

3 - Extend the sloop.models.DeviceBaseClass class and create your own pushtoken device model.

4 - Make sure that you fill necessary information at the settings file:

```
# Push Notification Settings (For AMAZON SNS)
SLOOP_DEVICE_TOKEN_MODEL = 'profiles.DevicePushToken'
SLOOP_BACKEND = 'sloop.backends.SNSBackend'
SLOOP_AWS_REGION_NAME = 'eu-west-1'
SLOOP_IOS_APPLICATION_ARN = ''
SLOOP_ANDROID_APPLICATION_ARN = ''
```

5 - Add sloop.models.PushNotificationMixin to your UserProfile model.

Done!

