Reference for porter.yaml
The following is a full reference for all the fields that can be set in a porter.yaml file.
version - the version of the porter.yaml file. The below documentation is for v2.
name - the name of the app. Must be 31 characters or less. Must consist of lower case alphanumeric characters or ’-’, and must start and end with an alphanumeric character.
build - the build settings for the app. Only one of build or image can be set.
method - the build method for the app. Can be one of docker or pack.
context - the build context for the app.
dockerfile - the path to the Dockerfile for the app, if the method is docker.
builder - the builder image to use for the app, if the method is pack.
buildpacks - the buildpacks to use for the app, if the method is pack.
image - the image settings for the app. Only one of build or image can be set.
repository - the image repository.
tag - the image tag.
env - the environment variables for the app.
[envGroups] - a list of environment groups that will be attached to the app.
predeploy - the pre-deploy job for the app.
run - the run command for the pre-deploy job.
autoRollback - the auto-rollback settings for the app.
enabled - whether auto-rollback is enabled.
services - a list of services for this app.
name - the unique ID of the resource. Must be 31 characters or less. Must consist of lower case alphanumeric characters or ’-’, and must start and end with an alphanumeric character.
type - the type of service - being one of web, worker, or job.
run - the run command for the service.
instances - the number of instances of the service to run.
cpuCores - the number of CPU cores to allocate to the service.
ramMegabytes - the amount of RAM to allocate to the service.
gpuCoresNvidia - the number of Nvidia GPU cores to allocate to the service.
port - the port that the service will listen on.
connections - a list of external connections for the service.
additional type-specific fields. See full reference for web, worker, and job services.
​
version

string - required

Copy
version: v2
​
name

string - optional
Either name must or the PORTER_APP_NAME environment variable must be set when running porter apply.

Copy
name: my-app
​
build

object - optional

Copy
build:
  method: pack
  context: .
  builder: heroku/buildpacks:20
  buildpacks:
    - heroku/python
​
image

object - optional

Copy
image:
  repository: my-registry/my-app
  tag: latest
​
env

object - optional

Copy
env:
  PORT: 8080
​
predeploy

object - optional

Copy
predeploy:
  run: echo "predeploy"
​
autoRollback

object - optional
When this attribute is enabled, Porter will automatically rollback all services in the app to the latest previously successfully-deployed version if the any service of the new version fails to deploy.

Copy
autoRollback:
  enabled: true
​
services

array - required

Copy
services:
  - name: web
    type: web
    run: python app.py
    instances: 1
    cpuCores: 1
    ramMegabytes: 1024
    port: 8080
​
connections

array - optional
Cloud SQL connection (GCP)

Copy
services:
  - name: web
    type: web
    run: python app.py
    instances: 1
    cpuCores: 1
    ramMegabytes: 1024
    port: 8080
    connections:
    - type: cloudSql
      config:
        cloudSqlConnectionName: project-123456:us-east1:instance-name
        cloudSqlDatabasePort: 5432
        cloudSqlServiceAccount: service-account-name
        # service accounts must be connected through
        # the Connections tab under the application's cluster
AWS role connection
Note: The AWS role connection feature is currently in development so may be subject to change.

Copy
services:
  - name: web
    type: web
    run: python app.py
    instances: 1
    cpuCores: 1
    ramMegabytes: 1024
    port: 8080
    connections:
    - type: awsRole
      role: iam-role-name
Overview
Deploying Multiple Apps with porter.yaml

