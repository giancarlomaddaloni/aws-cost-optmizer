
import * as cdk from 'aws-cdk-lib';
import { aws_iam as iam  } from 'aws-cdk-lib';
import { aws_lambda as lambda  } from 'aws-cdk-lib';
import { aws_ssm as ssm  } from 'aws-cdk-lib';
import { aws_events as events } from 'aws-cdk-lib';
import { aws_events_targets as targets } from 'aws-cdk-lib';
import { Size, Duration } from 'aws-cdk-lib';



export interface lambdavolumeCleanerProps extends cdk.StackProps {
  readonly environment: string;
  readonly projectName: string;
  readonly maxdaysVolume: string;
  readonly maxdaysVolumeUnvalidated: string;
  readonly maxdaysVolumenNotified: string;
  readonly eventsNotifications: string;
  
};

export class lambdavolumeCleaner extends cdk.Stack {
    
    private volumeKillerlambdaFunction: lambda.IFunction;
    private volumeListinglambdaFunction: lambda.IFunction;




    constructor(scope: cdk.App, id: string, props: lambdavolumeCleanerProps ) {
       
      super(scope, id, props);

      const { environment } = props;
      const { projectName }  = props;
      const { maxdaysVolume }  = props;
      const { maxdaysVolumeUnvalidated }  = props;
      const { maxdaysVolumenNotified }  = props;
      const { eventsNotifications }  = props;


      const eventsnotificationNumber: number = +eventsNotifications;
      let eventsNotification = eventsnotificationNumber / 60;
       
      const lambdaPolicy = new iam.PolicyStatement();

      lambdaPolicy.addActions("s3:*");
      lambdaPolicy.addActions("dynamodb:*");
      lambdaPolicy.addActions("logs:*");
      lambdaPolicy.addActions("cloudwatch:*");
      lambdaPolicy.addActions("ec2:*");
      lambdaPolicy.addActions("sts:assumeRole");
      lambdaPolicy.addActions("ses:SendEmail");



      lambdaPolicy.addResources("*");

      const lambdaRole = new iam.Role(this,`${projectName}-role-${environment}`, 
      {
        roleName: `${projectName}-${environment}`,
        assumedBy: new iam.CompositePrincipal(
        new iam.ServicePrincipal("lambda.amazonaws.com"),),
        description: 'A role intended to be utilized by Lambda KANU SRE team for Clean UP operations',
      });

      lambdaRole.addToPolicy(lambdaPolicy);
      lambdaRole.grantAssumeRole(new iam.ArnPrincipal(`${lambdaRole.roleArn}`));

      const volumeKillerlambdaFunction = () => {

        let lambdaFunction = new lambda.Function(this, `${projectName}-lambdavolumeKiller-${environment}`, {
          code: lambda.Code.fromAsset('lib/lambda-functions/volumeKiller',),
          functionName: `${projectName}-killer-${environment}`,
          role: lambdaRole,
          handler: "lambda_function.lambda_handler",
          memorySize: 4096,
          ephemeralStorageSize: Size.mebibytes(2056),
          runtime: lambda.Runtime.PYTHON_3_8,
          timeout: cdk.Duration.minutes(3),
          environment: {
            ROLE_ARN: `${lambdaRole.roleArn}`,
            TABLE_NAME: `${projectName}-${environment}`,
            MAX_DAYS_PER_VOLUME_NOTIFIED: `${maxdaysVolumenNotified}`,
            REGIONS: `['us-east-1','us-east-2','us-west-1','us-west-2','eu-central-1','eu-west-1','eu-west-2','eu-south-1','eu-west-3','eu-north-1']`,
            REGION: `${cdk.Stack.of(this).region}`,
            ACCOUNT: `${cdk.Stack.of(this).account}`,
          },
        });

        return lambdaFunction;

      };

      this.volumeKillerlambdaFunction = volumeKillerlambdaFunction();



      const volumeListinglambdaFunction = () => {

        let lambdaFunction = new lambda.Function(this, `${projectName}-lambdavolumeListing-${environment}`, {
          code: lambda.Code.fromAsset('lib/lambda-functions/volumeListing',),
          functionName: `${projectName}-listing-${environment}`,
          role: lambdaRole,
          handler: "lambda_function.lambda_handler",
          memorySize: 4096,
          ephemeralStorageSize: Size.mebibytes(2056),
          runtime: lambda.Runtime.PYTHON_3_8,
          timeout: cdk.Duration.minutes(3),
          environment: {
            ROLE_ARN: `${lambdaRole.roleArn}`,
            TABLE_NAME: `${projectName}-${environment}`,
            MAX_DAYS_PER_VOLUME: `${maxdaysVolume}`,
            MAX_DAYS_PER_VOLUME_UNVALIDATED: `${maxdaysVolumeUnvalidated}`,
            MAX_DAYS_PER_VOLUME_NOTIFIED: `${maxdaysVolumenNotified}`,
            REGIONS: `['us-east-1','us-east-2','us-west-1','us-west-2','eu-central-1','eu-west-1','eu-west-2','eu-south-1','eu-west-3','eu-north-1']`,
            REGION: `${cdk.Stack.of(this).region}`,
            ACCOUNT: `${cdk.Stack.of(this).account}`,
          },
        });

        return lambdaFunction;

      };

      this.volumeListinglambdaFunction = volumeListinglambdaFunction();


      // new ssm.StringParameter(this, `${projectName}_roleARN_${environment}`, {
      //   parameterName: `${projectName}_roleARN_${environment}`,
      //   stringValue: `${this.volumeCleanerlambdaFunction.functionArn}`,
      // });

      const eventsBus = new events.EventBus(this, `${projectName}-volumeCleanerBus-${environment}`, {
        eventBusName: `${projectName}-volumeCleanerTrigger-${environment}`
      });

      // const killernotificationsRule = new events.Rule(this, `${projectName}-killervolumeCleanerRule-${environment}`, {
      //   schedule: events.Schedule.rate( cdk.Duration.minutes(eventsNotification) )
      // });
      
      // const listingnotificationsRule = new events.Rule(this, `${projectName}-listingvolumeCleanerRule-${environment}`, {
      //   schedule: events.Schedule.rate( cdk.Duration.minutes(eventsNotification) )
      // });

      const killernotificationsRule = new events.Rule(this, `${projectName}-killervolumeCleanerRule-${environment}`, {
        schedule: events.Schedule.rate( cdk.Duration.hours(24) )
      });
      
      const listingnotificationsRule = new events.Rule(this, `${projectName}-listingvolumeCleanerRule-${environment}`, {
        schedule: events.Schedule.rate( cdk.Duration.hours(24) )
      });
      
      killernotificationsRule.addTarget( new targets.LambdaFunction( this.volumeKillerlambdaFunction, {
        maxEventAge: cdk.Duration.hours(2),
        retryAttempts: 2, 
      }));

      listingnotificationsRule.addTarget( new targets.LambdaFunction( this.volumeListinglambdaFunction, {
        maxEventAge: cdk.Duration.hours(2),
        retryAttempts: 2, 
      }));



    };
};


// -----------------------------------------------------------------------------------------------------------
// -----------------------------------------------------------------------------------------------------------
// --------------------------------- VMWare - SRE - GiancarloMaddaloni ---------------------------------------
