from __future__ import print_function # Python 2/3 compatibility
import boto3
import json
import decimal
import datetime
from boto3.dynamodb.conditions import Key, Attr

# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)
def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
    
    table = dynamodb.Table('meteroutage')
    
    fe = Key('year').between(1950, 1959);
    pe = "#yr, title, info.rating"
    # Expression Attribute Names for Projection Expression only.
    ean = { "#yr": "year", }
    esk = None
    
    
    response = table.scan()
    gfeatures = []
    timeouton = str(datetime.datetime.now() - datetime.timedelta(minutes=4))
    print('back on time is: {timeouton}'.format(timeouton=timeouton))
    
    for i in response['Items']:
        print(json.dumps(i, cls=DecimalEncoder))
        if (i['mytime'] <= timeouton):
            pointcolor = '#FF0000'
        else:
            pointcolor = '#00FF00'
        gfeature = {
            'type': 'Feature',
            'geometry':{
            'type': 'Point',
            'coordinates': [float(i['longitude']),float(i['latitude'])]
            },
            'properties':{
            'title': i['meternumber'],
            'marker-color': pointcolor
            }
        }
        gfeatures.append(gfeature)
    
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            ExclusiveStartKey=response['LastEvaluatedKey']
            )
    
        for i in response['Items']:
            print(json.dumps(i, cls=DecimalEncoder))
    geometries = {
    'type': 'FeatureCollection',
    'features': gfeatures,
    }
    print(json.dumps(geometries))
    return(geometries)