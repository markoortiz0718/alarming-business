from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cloudwatch_actions,
    aws_events as events,
    aws_events_targets as events_targets,
    aws_sns as sns,
    aws_sqs as sqs,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
)
from constructs import Construct


class AlarmingBusinessStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, environment: dict, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.eventbridge_minute_scheduled_event = events.Rule(
            self,
            "RunEveryMinute",
            event_bus=None,  # "default" bus
            schedule=events.Schedule.rate(Duration.minutes(1)),
        )
        self.sqs_queue = sqs.Queue(
            self,
            "SQSQueue",
            removal_policy=RemovalPolicy.DESTROY,
            retention_period=Duration.days(4),
            visibility_timeout=Duration.seconds(30),
            queue_name=environment["SQS_QUEUE"],
        )
        self.sns_topic = sns.Topic(
            self, "SNSTopic", topic_name=environment["SNS_TOPIC"]
        )
        # Step Function
        send_sqs_message = sfn_tasks.SqsSendMessage(
            self,
            "SendSQSMessage",
            queue=self.sqs_queue,
            message_body=sfn.TaskInput.from_object(
                {"greetings.$": "$$.State.EnteredTime"}
            ),
        )
        self.state_machine = sfn.StateMachine(
            self, "TroublesomeMessenger", definition=send_sqs_message
        )

        # connect AWS resources
        self.eventbridge_minute_scheduled_event.add_target(
            target=events_targets.SfnStateMachine(
                machine=self.state_machine,
                input=None,
                # dead_letter_queue=dlq,  # might consider for high availability
            )
        )
        self.alarm = cloudwatch.Alarm(
            self,
            "SQSMessagesPilingUp",
            metric=self.sqs_queue.metric_approximate_number_of_messages_visible().with_(
                period=Duration.minutes(1)
            ),
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            threshold=5,
            evaluation_periods=1,
        )
        alarm_action = cloudwatch_actions.SnsAction(topic=self.sns_topic)
        self.alarm.add_alarm_action(alarm_action)
        self.alarm.add_ok_action(alarm_action)
