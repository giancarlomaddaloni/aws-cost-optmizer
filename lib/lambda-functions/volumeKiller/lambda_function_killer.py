# Steps
# 1) Count all the volumes available within the region of the function execution. 
# 2) Save the volumeID, a confirmation checkpoint of a screenshot, a timestamp and a tag to dynamoDB.
# 3) Analyze the values 15 days after by an event bus trigger  --> if the EBS is still in 'available' state && timestamp > 15 (days) && screenshoot === true --> DELETE EBS

import json, boto3, os, botocore, base64, time
from botocore.exceptions import ClientError
from datetime import datetime, timedelta, timezone

def lambda_handler(event, context):
    

    class context:
        
        def __init__ (self):



            self.now = datetime.now()
            self.timestamp = self.now.strftime("%d%m%Y%H%M%S")
            
            ## Dynamo DB table for storing the record of the available volumes
            self.tableName = str(os.environ['TABLE_NAME'])
            self.account = str(os.environ['ACCOUNT'])
            
            self.maxdaysVolumenNotified = str(os.environ['MAX_DAYS_PER_VOLUME_NOTIFIED'])


            # self.roleARN = str(os.environ['ROLE_ARN'])
            self.region = str(os.environ['REGION'])
            #self.regions = os.environ['REGIONS']
            self.regions = ['us-east-1','us-east-2','us-west-1','us-west-2','eu-central-1','eu-west-1','eu-west-2','eu-south-1','eu-west-3','eu-north-1']


     
    class logic:
        
        c = context ()
        
        def add_toDynamo (self,item):
            dynamodb = boto3.client('dynamodb')
            try :
                
               response = dynamodb.put_item(TableName=c.tableName, Item=item)
               return response
            except botocore.exceptions.ClientError as e:
                
                if e.response['Error']['Code'] == 'AuthFailure':
                    print("You need to create a new token")
                    
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    print("No volume available")
        
                
        def get_attachedEBSTrail(self,region,days):
            

            startDateTime = datetime.now(tz=timezone.utc) - timedelta(days=days)
            cloudTrailClient = boto3.client('cloudtrail', region_name=region)
            attrList = [{ 'AttributeKey': 'EventName','AttributeValue':'AttachVolume'}]
            attachedVolumesTrail = 'None'
            
            try :
                
                attachedVolumesTrail_Prev = cloudTrailClient.lookup_events(LookupAttributes=attrList, StartTime=startDateTime, EndTime=datetime.now(tz=timezone.utc), MaxResults=100)
                if attachedVolumesTrail_Prev: 
                   attachedVolumesTrail = attachedVolumesTrail_Prev
                return attachedVolumesTrail

                
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'AuthFailure':
                    print("You need to create a new token")
                
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    print("No volume available")
        
        def list_snapshotAge (self,region,snapshotID):
            
            ec2client = boto3.client('ec2', region)
            snapshotsAge = 'None'

            try :
                snapshots = ec2client.describe_snapshots(OwnerIds=[c.account], SnapshotIds=[snapshotID])

                for snapshot in snapshots['Snapshots']:
                    snapshotsAge = snapshot['StartTime']
                
                return snapshotsAge

            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'AuthFailure':
                    print("You need to create a new token")
                
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    print("No snapshot available")         


        def get_ebsDynamoRecords(self):
            
            dynamodb = boto3.client('dynamodb')

            try :
                
                items = dynamodb.scan(TableName=c.tableName).get('Items')
                return items            

            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'AuthFailure':
                    print("You need to create a new token")
                
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    print("No volume available")

        def delete_EBS (self,region,volumeID):
            ec2client = boto3.client('ec2',region_name=region)
            try :
                # Enable to delete
                # deleteEBS = ec2client.delete_ebs(volumeID=volumeID)

                return 'deleted'
        
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'AuthFailure':
                    print("You need to create a new token")
                
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    print("No volume available")

                    

    c = context()
    l = logic()
    
    
    ## Maximum amount of days that an EBS will be kept if a cloudtrail for the volumeID is found as part of 'DetachVolume' event.
    maxdaysVolumenNotified = 1

    
    finalNoticeVolumes = []
    print (finalNoticeVolumes)

    # for region in c.regions :
        
    c.region = 'us-east-1'
    
    maxdaysVolumenNotified_epoch = datetime.now(tz=timezone.utc) - timedelta(minutes=maxdaysVolumenNotified)

    
    # 1) Initial validation for a volume to be deleted based on the 'AttachVolume' event name from cloudtrail.
    # Filtering trails by the attributes --> {'AttributeKey': 'ResourceType', 'AttributeValue': 'AWS::EC2::Volume'},{ 'AttributeKey': 'EventName','AttributeValue':'AttachVolume'}
    # Filtering timing set at max for cloudtrail events, set as maxdaysVolumenNotified.
    attachedEBSTrail = l.get_attachedEBSTrail(c.region,maxdaysVolumenNotified)
    
    attachedVolumesID = []
    
    for attachedEBS in attachedEBSTrail['Events']:
        attachedEBSTime = attachedEBS['EventTime']
        for ebs in attachedEBS['Resources']:
            if ebs['ResourceType'] == 'AWS::EC2::Volume' and attachedEBSTime < maxdaysVolumenNotified_epoch :
                attachedVolumesID.append(['ResourceName'])
                
    # print (attachedVolumesID)

    ebsDynamoRecords = l.get_ebsDynamoRecords()
    # print (ebsDynamoRecords)
            
    
    if ebsDynamoRecords : 
        
        # Setting attribute to false by default, this will be modified based on conditions to deletion
        ebsDeleteStatus = 'false'
        ebsStatus = 'deleting'
    
        for ebsItem in ebsDynamoRecords: 
            

        
            if ebsItem['ebsStatus']['S'] == 'deleting' and ebsItem['snapshotID']['S'] != 'false' :
                snapshotID = ebsItem['snapshotID']['S']
                volumeID = ebsItem['volumeID']['S']
                volumeTags = ebsItem['volumeTags']['S']


                for region in c.regions :
        
                    snapshotAge = l.list_snapshotAge (region,snapshotID)
                    
                    if snapshotAge:
                    # Conditions for setting up ebsDeleteStatus to true and be removed 
                        # print (str(snapshotAge)+"----"+str(maxdaysVolumenNotified_epoch))
        
                        if snapshotAge < maxdaysVolumenNotified_epoch and volumeID not in attachedVolumesID:
                            ebsDeleteStatus = 'true'
   
                        elif snapshotAge > maxdaysVolumenNotified_epoch:
                            ebsDeleteStatus = 'false'
                        
                    if ebsDeleteStatus == 'true':
                        ebsStatus = l.delete_EBS(region,volumeID)
                        
                    
                    item = {"volumeID": {'S':volumeID},"ebsStatus":{'S':str(ebsStatus)},"snapshotID":{'S':str(snapshotID)},"ebsRegion":{'S':str(region)},"volumeTags":{'S':str(volumeTags)}}

                    l.add_toDynamo(item)

    return {
        'statusCode': 200,
    }



###------------------------
