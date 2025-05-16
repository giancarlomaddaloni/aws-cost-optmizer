#!/usr/bin/env node

import * as cdk from "aws-cdk-lib";

import { lambdavolumeCleaner } from '../lib/lambda-volumeCleaner-stack';
import { dynamoResources } from '../lib/dynamoDB-stack';


const app = new cdk.App();


function validateString(parameter: string){
  let variable = `${app.node.tryGetContext(parameter)}`
  if (variable === undefined || !(typeof(variable) === 'string') || variable.trim() === '') {
    variable = 'false';
    throw new Error(`Must pass a '-c parameter=<parameter>' context ${parameter}`);
  }
  return variable;
  
};

function capitalizeFirstLetter(string: string) {
  return string.charAt(0).toUpperCase() + string.slice(1);
};

// General Variables
let region = validateString("region");
let account = validateString("account");
let projectName = validateString("projectName");
let environment = validateString("environment");
let eventsNotifications = validateString("eventsNotifications");

let maxdaysVolumenNotified = validateString("maxdaysVolumenNotified")
let maxdaysVolume = validateString("maxdaysVolume")
let maxdaysVolumeUnvalidated = validateString("maxdaysVolumeUnvalidated")

        
function stacktenant() {

  let stacktenant = `${capitalizeFirstLetter(projectName)}-${capitalizeFirstLetter(environment)}`;
  return stacktenant;

};

const lambda_volumeCleaner = new lambdavolumeCleaner(app, `${projectName}-function-${environment}`, {
  stackName:`lambda-${stacktenant()}`,
  projectName: projectName,
  environment: environment,
  eventsNotifications: eventsNotifications,
  maxdaysVolumenNotified: maxdaysVolumenNotified,
  maxdaysVolume: maxdaysVolume,
  maxdaysVolumeUnvalidated: maxdaysVolumeUnvalidated,
  env: {
    region: region,
    account: account,
  },
});




const dynamo_Resources = new dynamoResources(app, `${projectName}-db-${environment}`, {
  stackName:`dynamoResources-${stacktenant()}`,
  projectName: projectName,
  environment: environment,
  env: {
    region: region,
    account: account,
  },
});


app.synth();
