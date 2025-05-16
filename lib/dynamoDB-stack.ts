
import * as cdk from 'aws-cdk-lib';
import { aws_dynamodb as dynamodb  } from 'aws-cdk-lib';
import { aws_iam as iam  } from 'aws-cdk-lib';
import { aws_ec2 as ec2  } from 'aws-cdk-lib';

export interface dynamoResourcesProps extends cdk.StackProps {
  readonly environment: string;
  readonly projectName: string;
};



export class dynamoResources extends cdk.Stack {
    
    private dynamoDBvolumeCleaner: dynamodb.Table;



    constructor(scope: cdk.App, id: string, props: dynamoResourcesProps ) {
       
       super(scope, id, props);

       const { environment } = props;
       const { projectName }  = props;

      // ----------------------------------------------------------------

      // -----------------------    DYNAMODB   --------------------------
      // ----------------------------------------------------------------


      // DynamoDB table for Registring volumeID's and records for the functionality of the lambda function


      this.dynamoDBvolumeCleaner = new dynamodb.Table(this, `${projectName}-volumeCleanerDB-${environment}`, {
        partitionKey: {
          name: 'volumeID',
          type: dynamodb.AttributeType.STRING
        },
        // sortKey: {name: 'lastUpdate', type: dynamodb.AttributeType.NUMBER},
        tableName: `${projectName}-${environment}`,
        billingMode: dynamodb.BillingMode.PROVISIONED,
        
        // Global table for redundancy, enable multiregion.
        // Adding all regions where lambda functions are being invoked --> global table for redundancy
        // Except the regino in which this script is being deployed.
        // replicationRegions: [ 'us-east-2', 'us-west-1', 'us-west-2'] // --> EBS Volumes in other regions,

      });

      this.dynamoDBvolumeCleaner.autoScaleWriteCapacity({
        minCapacity: 2,
        maxCapacity: 4,
      }).scaleOnUtilization({ targetUtilizationPercent: 90 });



      this.dynamoDBvolumeCleaner.autoScaleReadCapacity({
        minCapacity: 2,
        maxCapacity: 4,
      }).scaleOnUtilization({ targetUtilizationPercent: 90 });



    };
};


// -----------------------------------------------------------------------------------------------------------
// -----------------------------------------------------------------------------------------------------------
// --------------------------------- VMWare - SRE - GiancarloMaddaloni ---------------------------------------
