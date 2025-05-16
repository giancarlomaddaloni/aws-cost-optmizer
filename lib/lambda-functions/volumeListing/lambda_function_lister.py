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
            
            self.maxdaysVolume = os.environ['MAX_DAYS_PER_VOLUME']
            self.maxdaysVolumeUnvalidated = os.environ['MAX_DAYS_PER_VOLUME_UNVALIDATED']
            self.maxdaysVolumenNotified = os.environ['MAX_DAYS_PER_VOLUME_NOTIFIED']

            self.region = str(os.environ['REGION'])
            self.account = str(os.environ['ACCOUNT'])
            self.roleARN = str(os.environ['ROLE_ARN'])

            # self.regions = str(os.environ['REGIONS'])
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
                    
                    
                    
        def get_ebsDynamoRecord (self,volumeID):
            dynamodb = boto3.client('dynamodb')
            try :
                
               ebsDynamoItem = dynamodb.get_item(TableName=c.tableName, Key={'volumeID': {'S': volumeID}})
               return ebsDynamoItem

            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'AuthFailure':
                    print("You need to create a new token")
                
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    print("No volume available")
                    
                    
        
        def get_detachedEBSTrail(self,region):
            
            # gets CloudTrail events from startDateTime until "now"
            # The maximum searchable time is 90 days
            startDateTime = datetime.now(tz=timezone.utc) - timedelta(days=90)
            cloudTrailClient = boto3.client('cloudtrail', region_name=region)
            attrList = [{ 'AttributeKey': 'EventName','AttributeValue':'DetachVolume'}]
            detachedVolumesTrail = 'None'
            
            try :
                
                detachedVolumesTrail_Prev = cloudTrailClient.lookup_events(LookupAttributes=attrList, StartTime=startDateTime, EndTime=datetime.now(tz=timezone.utc), MaxResults=100)
                if detachedVolumesTrail_Prev: 
                   detachedVolumesTrail = detachedVolumesTrail_Prev
                return detachedVolumesTrail

                
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'AuthFailure':
                    print("You need to create a new token")
                
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    print("No volume available")


        def get_volumesAvailable (self,region):
            ec2client = boto3.client('ec2', region_name=region)
            try :
                
                volumesAvailable=ec2client.describe_volumes( Filters=[{'Name': 'status', 'Values': ['available']}])
                return volumesAvailable
                
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'AuthFailure':
                    print("You need to create a new token")
                
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    print("No volume available")
                    

        def create_Snapshot(self,region,volumeID):
            
            ec2client = boto3.client('ec2',region_name=region)
            snapshotID = 'None'

            try:

                createSnapshot = ec2client.create_snapshot( 
                    Description='Created by Lambda backup function ebs available snapshots prior removal', 
                    VolumeId= volumeID, 
                    DryRun= False)
                    
                snapshotID = str(createSnapshot['SnapshotId'])
                time.sleep (3)
                
                return snapshotID

            except botocore.exceptions.ClientError as e:
                

                if e.response['Error']['Code'] == 'AuthFailure':
                    print("You need to create a new token")
                
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    print("No volume available")


        def send_Email (self, finalNoticeVolumes):
           
           
            sesClient = boto3.client ('ses')
            
            body_html = f"""<html>
                    <head></head>
                    <body>
                      <h1>The following volumes will be deleted within the next {str(c.maxdaysVolumenNotified)} days</h1>
                      <br/>
                      <p>{str(finalNoticeVolumes)}</p> 
                      <br/>
                      <p>If you would like to know more information about the volume, create a query with the volumeID to the dynamoDB table '{c.tableName}' in region '{c.region}' within the KANU account '{c.account}'.</p> 
                      <br/>
                      <h3>KANU SRE Team<h3>
                    </body>
                    </html>
                          """
    
            email_message = {
                    'Body': {
                        'Html': {
                            'Charset': 'utf-8',
                            'Data': body_html,
                        },
                    },
                    'Subject': {
                        'Charset': 'utf-8',
                        'Data': "AWS Cost Efectiveness Tool within the KANU account --> "+c.account,
                    },
                }
                
            

            try:
                sendEmail = sesClient.send_email(Source='kanu@example.com',Destination={'ToAddresses': ['kanu@example.com']},Message=email_message,Tags=[{'Name': 'Timestamp','Value': str(c.timestamp)}])
                print ("Sending Email to kanu@example.com account")
                return sendEmail

            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'MessageRejected':
                    sendEmail = "The message was rejected."
                if e.response['Error']['Code'] == 'MailFromDomainNotVerifiedException':
                    sendEmail = "You must verified the source of the email."
                    

    c = context()
    l = logic()
    
    
    ## Maximum amount of days that an EBS will be kept if a cloudtrail for the volumeID is found as part of 'DetachVolume' event.
    maxdaysVolume = 7
    # maxdaysVolume = 21

    ## Maximum amount of days that an EBS will be kept if a cloudtrail for the volumeID is NOT found but it's on 'Available' state.
    maxdaysVolumeUnvalidated = 14
    # maxdaysVolumeUnvalidated = 63
    
    finalNoticeVolumes = []
    print (finalNoticeVolumes)

    for region in c.regions :
        
        # c.region = region
        
        maxdaysVolume_epoch = datetime.now(tz=timezone.utc) - timedelta(days=maxdaysVolume)
        maxdaysVolumeUnvalidated_epoch = datetime.now(tz=timezone.utc) - timedelta(days=maxdaysVolumeUnvalidated)

        
        # 1) Initial validation for a volume to be deleted based on the 'DetachVolume' event name from cloudtrail.
        # Filtering trails by the attributes --> {'AttributeKey': 'ResourceType', 'AttributeValue': 'AWS::EC2::Volume'},{ 'AttributeKey': 'EventName','AttributeValue':'DetachVolume'}
        # Filtering timing set at max for cloudtrail events, which is 90 days.
        detachedEBSTrail = l.get_detachedEBSTrail(region)
        
        dettachedVolumesID = []
        
        for detachedEBS in detachedEBSTrail['Events']:
            detachedEBSTime = detachedEBS['EventTime'].date()
            for ebs in detachedEBS['Resources']:
                if ebs['ResourceType'] == 'AWS::EC2::Volume' and detachedEBSTime < maxdaysVolume_epoch.date() :
                    dettachedVolumesID.append(['ResourceName'])


                            
        ## 2) Second validation for a volume to be deleted based on the 'Available' state of the EBS
        # Listing every EBS resource that's currently on 'Available' state.
        # Extracting metadata and attributes from each Item
        
        # Listing all volumes within this region filtered by -->  {'Name': 'status', 'Values': ['available']}
        volumesAvailable = l.get_volumesAvailable(region)
        
        
        # Loping the volumesAvailable list
        # Validating data within dynamoDB previously gathered
        # Validating snapshotID.
        for ebsItem in volumesAvailable['Volumes']:
            
            
            ## Setting variables for Item
            # A final notice attribute is set to a date if an email has been sent for the first time about the scheduled deletion, validated by ebsDynamoRecord
            ebsStatus = 'false'
            
            # Setting snapshotID to false since one has to be created in order to retrive an ID. 
            snapshotID = 'false'

            # Setting attribute to false by default, this will be modified based on conditions to deletion
            ebsDeleteStatus = 'false'
            
            volumeID = ebsItem['VolumeId']
            volumeCreatedtime = ebsItem['CreateTime'].date()
            # volumeSize = ebsItem['Size']
            volumeTags = []
            
            
            # Seting tags as a dynamo attribute if exists per volumeID
            if 'Tags' in ebsItem:
                for tag in ebsItem['Tags']:
                    volumeTags.append(tag)
                pass
            else:
                pass
            

            # Conditions for setting up ebsDeleteStatus to true and be removed 
            if volumeCreatedtime > maxdaysVolume_epoch.date():
                ebsDeleteStatus = 'false'

            if volumeCreatedtime < maxdaysVolume_epoch.date() and volumeID in dettachedVolumesID :
                ebsDeleteStatus = 'true'

            elif volumeCreatedtime < maxdaysVolumeUnvalidated_epoch.date():
                ebsDeleteStatus = 'true'



                        
            if ebsDeleteStatus == 'true' :
                
                # Validating if screenshot if neccesary
                # Calling dynamo Item in order to retrieve snapshotID data.
                # If not snapshotID date is found within the dynamoDB table, a new snapshot will be created.
                ebsDynamoRecord = l.get_ebsDynamoRecord(volumeID)
                # print (ebsDynamoRecord)
                
                
                if ebsDynamoRecord : 
                    
                    # if ebsDynamoRecord['Item']['ebsStatus']['S'] != 'deleted':
                    
                        if 'Item' in ebsDynamoRecord :

                                if ebsDynamoRecord['Item']['snapshotID']['S'] == 'false':
                                    snapshotID = l.create_Snapshot(region,volumeID)
                                    
                                if ebsDynamoRecord['Item']['snapshotID']['S'] != 'false':
                                    snapshotID = ebsDynamoRecord['Item']['snapshotID']['S']
                                    
                                if ebsDynamoRecord['Item']['ebsStatus']['S'] == 'false':
                                    ebsStatus = ebsDynamoRecord['Item']['ebsStatus']['S']
                                    ebsStatus = 'deleting'
                                    finalNoticeVolumes.append({"Volume : "+volumeID+" in region "+region})

                        
                                if ebsDynamoRecord['Item']['ebsStatus']['S'] == 'deleting':
                                   ebsStatus = ebsDynamoRecord['Item']['ebsStatus']['S']
                                   finalNoticeVolumes.append({"Volume : "+volumeID+" in region "+region})

                                if ebsDynamoRecord['Item']['ebsStatus']['S'] == 'deleted':
                                    ebsStatus = ebsDynamoRecord['Item']['ebsStatus']['S']

                                    
                                print ("Checkpoint item")

                                # print ("volumeID",volumeID,"region",region)
        
                        else : 
                            print ("Checkpoint no item")
                            snapshotID = l.create_Snapshot(region,volumeID)
                            ebsStatus = 'deleting'
                            finalNoticeVolumes.append({"Volume : "+volumeID+" in region "+region})
                            # print ("volumeID",volumeID,"region",region)
    
         

            # item = {"volumeID": {'S':volumeID},"volumeCreatedtime":{'S':str(volumeCreatedtime)},"volumeSize":{'S':str(volumeSize)},"ebsDeleteStatus":{'S':ebsDeleteStatus},"ebsCheckedOn":{'S':str(ebsCheckedOn)},"finalNotice":{'S':finalNotice},"snapshotID":{'S':str(snapshotID)},"volumeTags":{'S':str(volumeTags)} }
            item = {"volumeID": {'S':volumeID},"ebsStatus":{'S':str(ebsStatus)},"snapshotID":{'S':str(snapshotID)},"ebsRegion":{'S':str(region)},"volumeTags":{'S':str(volumeTags)}}

            
            l.add_toDynamo(item)
        
    print (finalNoticeVolumes)
    l.send_Email(finalNoticeVolumes)

    return {
        'statusCode': 200,
    }



###------------------------
