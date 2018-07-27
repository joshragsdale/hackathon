import math
import dateutil.parser
import datetime
import time
import decimal
import os
import logging
import boto3
from botocore.exceptions import ClientError
import json

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)


""" --- Helpers to build responses which match the structure of the necessary dialog actions --- """


def get_slots(intent_request):
    return intent_request['currentIntent']['slots']


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }


""" --- Helper Functions --- """

def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            "isValid": is_valid,
            "violatedSlot": violated_slot,
        }

    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }

def agenda_item_by_time(intent_request,intent_name):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    
    requestedtime = get_slots(intent_request)["agendaitemtime"]
    dtrequestedtime = datetime.datetime.strptime(requestedtime, '%H:%M').time()
    table = dynamodb.Table('foundationdayagenda')
    response = table.scan()
    matchfound = 0
    for i in response['Items']:
        dtstarttime = datetime.datetime.strptime(i['starttime'], '%H:%M').time()
        dtendtime = datetime.datetime.strptime(i['endtime'], '%H:%M').time()
        if (dtrequestedtime >= dtstarttime and dtrequestedtime < dtendtime):
            matchfound = 1
            itemsubject = i['subject']
            break
    if (matchfound == 1):
        output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
        fulfillment_state = 'Fulfilled'
        message = {'contentType': 'PlainText',
                    'content': 'At {} we will be on {}'.format(requestedtime,itemsubject)}
    
        response = {
            'sessionAttributes': output_session_attributes,
            'dialogAction': {
                  'type': 'Close',
                  'fulfillmentState': fulfillment_state,
                  'message': message
                }
        }
        return response
    else:
        slots = get_slots(intent_request)
        validation_result = build_validation_result(False, 'agendaitemtime', 'I did not an agend item at {}. What time did you want?'.format(requestedtime))
        return elicit_slot(intent_request['sessionAttributes'],
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])
    
def agenda_item_by_order(intent_request,intent_name):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    
    table = dynamodb.Table('foundationdayagenda')
    #agendaitem = 1
    agendaitem = int(get_slots(intent_request)["agendaitemorder"])
    try:
        dyresponse = table.get_item(
            Key={
                'slot': agendaitem
            }
        )
        item = dyresponse['Item']['subject']
    except Exception as e:
        slots = get_slots(intent_request)
        validation_result = build_validation_result(False, 'agendaitemorder', 'I did not find that agenda item.  Which item did you want?')
        return elicit_slot(intent_request['sessionAttributes'],
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])
    else:
        output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
        fulfillment_state = 'Fulfilled'
        message = {'contentType': 'PlainText',
                    'content': 'Agenda item {} is: {}'.format(agendaitem,item)}

        response = {
            'sessionAttributes': output_session_attributes,
            'dialogAction': {
               'type': 'Close',
              'fulfillmentState': fulfillment_state,
              'message': message
            }
        }
        return response


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.debug('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']
    
    # Dispatch to your bot's intent handlers
    if intent_name == 'agendaitembyorder':
        return agenda_item_by_order(intent_request,intent_name)
    if intent_name == 'agendaitembytime':
        return agenda_item_by_time(intent_request,intent_name)   


    raise Exception('Intent with name ' + intent_name + ' not supported')
    
    

""" --- Main handler --- """


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))

    return dispatch(event)
