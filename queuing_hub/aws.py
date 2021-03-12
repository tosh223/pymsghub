import boto3

from queuing_hub.base import BasePublisher, BaseSubscriber

class AwsBase():

    def __init__(self, client=None):
        if client:
            self._client = client
        else:
            session = boto3.Session()
            self._client = session.client('sqs')
        self._queue_list = self._client.list_queues()['QueueUrls']


class AwsPublisher(AwsBase, BasePublisher):

    def __init__(self, client=None):
        AwsBase.__init__(self, client=client)
        BasePublisher.__init__(self)

    @property
    def topic_list(self):
        return self._queue_list

    def put(self, topic, body):
        response = self._client.send_message(
            QueueUrl = topic,
            MessageBody = body
        )
        return response


class AwsSubscriber(AwsBase, BaseSubscriber):

    ATTRIBUTE_NAMES = [
        'ApproximateNumberOfMessages',
        # 'ApproximateNumberOfMessagesDelayed',
        # 'ApproximateNumberOfMessagesNotVisible',
        # 'DelaySeconds',
        # 'MessageRetentionPeriod',
        # 'ReceiveMessageWaitTimeSeconds',
        # 'VisibilityTimeout'
    ]

    def __init__(self, client=None):
        AwsBase.__init__(self, client=client)
        BaseSubscriber.__init__(self)

    @property
    def subscription_list(self):
        return self._queue_list

    def qsize(self, subscription_list :list=None):
        response = {}
        if not subscription_list:
            subscription_list = self._queue_list

        for subscription in subscription_list:
            response[subscription] = self._get_message_count(subscription)
        
        return response

    def is_empty(self, subscription) -> bool:
        return self._get_message_count(subscription) == 0

    def purge(self, subscription):
        self._client.purge_queue(QueueUrl=subscription)

    def get(self, subscription, max_num=1):
        messages = []
        response = self._client.receive_message(
            QueueUrl=subscription,
            MaxNumberOfMessages=max_num
        )

        for message in response['Messages']:
            messages.append(message)
            self._task_done(subscription, message['ReceiptHandle'])

        return messages

    def _task_done(self, subscription, receipt_handle):
        self._client.delete_message(
            QueueUrl=subscription,
            ReceiptHandle=receipt_handle
        )

    def _get_message_count(self, subscription):
        attributes = self._get_attributes(subscription, self.ATTRIBUTE_NAMES)
        return int(attributes[self.ATTRIBUTE_NAMES[0]])

    def _get_attributes(self, subscription, attribute_names):
        response= self._client.get_queue_attributes(
            QueueUrl=subscription,
            AttributeNames=attribute_names
        )
        return response['Attributes']
