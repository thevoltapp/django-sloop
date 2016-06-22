import json
import re
import boto.sns
from django.conf import settings
from django.utils.importlib import import_module
from sloop.constants import *

def get_backend_class(import_path=None):
    module_path, class_name = (import_path or settings.SLOOP_BACKEND).rsplit('.', 1)
    module = import_module(module_path)
    return getattr(module, class_name)

class BaseBackend(object):

    def send_push_notification(self, message, url, badge_count, sound, extra, category, *args, **kwargs):
        """
        Sends push notification.
        """
        raise NotImplemented()

    def send_silent_push_notification(self, extra, badge_count, content_available, *args, **kwargs):
        """
        Sends silent push notification.
        """
        raise NotImplemented()

class SNSBackend(BaseBackend):
    """
    AWS SNS push notification sender
    """
    device = None
    connection = None

    def __init__(self, device):
        self.device = device
        self.connection = self.get_sns_connection()

    def get_sns_connection(self):
        if self.connection:
            return self.connection
        region = [r for r in boto.sns.regions() if r.name == settings.SLOOP_AWS_REGION_NAME][0]
        sns = boto.sns.SNSConnection(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region=region
        )
        return sns

    @property
    def application_arn(self):
        if self.device.device_type == DEVICE_PUSH_TOKEN_TYPE_IOS:
            application_arn = settings.SLOOP_IOS_APPLICATION_ARN
        elif self.device.device_type == DEVICE_PUSH_TOKEN_TYPE_ANDROID:
            application_arn = settings.SLOOP_ANDROID_APPLICATION_ARN
        else:
            assert False
        return application_arn

    def send_push_notification(self, message, url, badge_count, sound, extra, category, *args, **kwargs):
        """
        Sends push message using device token
        """
        if self.device.device_type == DEVICE_PUSH_TOKEN_TYPE_IOS:
            data = self.generate_apns_push_notification_message(message, url, badge_count, sound, extra, category, *args, **kwargs)
        else:
            data = self.generate_gcm_push_notification_message(message, url, badge_count, sound, extra, category, *args, **kwargs)
        return self._send_payload(data)

    def send_silent_push_notification(self, extra, badge_count, content_available, *args, **kwargs):
        """
        Sends silent push notification
        """
        if self.device.device_type == DEVICE_PUSH_TOKEN_TYPE_IOS:
            data = self.generate_apns_silent_push_notification_message(extra, badge_count, content_available, *args, **kwargs)
        else:
            data = self.generate_gcm_silent_push_notification_message(extra, badge_count, content_available, *args, **kwargs)
        return self._send_payload(data)

    def generate_gcm_push_notification_message(self, message, url, badge_count, sound, extra, category, *args, **kwargs):
        if url:
            extra['url'] = url
        data = {
            'url': url,
            'alert': message,
            'sound': sound,
            'custom': extra,
            'badge': badge_count,
            'category': category,
            'custom_url': url
        }

        data.update(kwargs)
        data_bundle = {
            'data': data
        }
        data_string = json.dumps(data_bundle, ensure_ascii=False)
        return {
            'GCM': data_string
        }

    def generate_gcm_silent_push_notification_message(self, extra, badge_count, content_available, *args, **kwargs):
        data = {
            'content-available': content_available,
            'sound': '',
            'badge': badge_count,
            'custom': extra
        }
        data.update(kwargs)
        data_bundle = {
            'data': data
        }
        data_string = json.dumps(data_bundle, ensure_ascii=False)
        return {
            'GCM': data_string
        }

    def generate_apns_push_notification_message(self, message, url, badge_count, sound, extra, category, *args, **kwargs):
        if url:
            extra["url"] = url
        data = {
            'url': url,
            'alert': message,
            'sound': sound,
            'custom': extra,
            'badge': badge_count,
            'category': category
        }
        data.update(kwargs)
        apns_bundle = {
            'aps': data
        }
        apns_string = json.dumps(apns_bundle, ensure_ascii=False)
        return {
            'APNS': apns_string
        }

    def generate_apns_silent_push_notification_message(self, extra, badge_count, content_available, *args, **kwargs):
        data = {
            'content-available': content_available,
            'sound': '',
            'badge': badge_count,
            'custom': extra
        }
        data.update(kwargs)
        apns_bundle = {
            'aps': data
        }
        apns_string = json.dumps(apns_bundle, ensure_ascii=False)
        return {
            'APNS': apns_string
        }

    def get_or_create_platform_endpoint_arn(self):
        try:
            endpoint_response = self.connection.create_platform_endpoint(
                platform_application_arn=self.application_arn,
                token=self.device.token,
            )
            endpoint_arn = endpoint_response['CreatePlatformEndpointResponse']['CreatePlatformEndpointResult']['EndpointArn']
        except boto.exception.BotoServerError, err:
            # Yes, this is actually the official way:
            # http://stackoverflow.com/questions/22227262/aws-boto-sns-get-endpoint-arn-by-device-token
            result_re = re.compile(r'Endpoint(.*)already', re.IGNORECASE)
            result = result_re.search(err.message)
            if result:
                endpoint_arn = result.group(0).replace('Endpoint ', '').replace(' already', '')
            else:
                raise
        return endpoint_arn

    def _send_payload(self, data):
        endpoint_arn = self.get_or_create_platform_endpoint_arn()
        message = json.dumps(data, ensure_ascii=False)
        if settings.DEBUG:
            print "ARN:" + endpoint_arn
            print message
        try:
            publish_result = self.connection.publish(
                target_arn=endpoint_arn,
                message=message,
                message_structure='json'
            )
            if settings.DEBUG:
                print publish_result
            return publish_result
        except boto.exception.BotoServerError, err: 
            print err
            return None
