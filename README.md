# tyk-sre-assignment

This repository contains the boilerplate projects for the SRE role interview assignments. There are two projects: one for Go and one for Python respectively.


### Python Project

Location: https://github.com/TykTechnologies/tyk-sre-assignment/tree/main/python

We suggest using a Python virtual env, e.g.:
```
python3 -m venv .venv
source .venv/bin/activate
```

Make sure to install the dependencies using `pip`:
```
pip3 install -r requirements.txt
```

To run it against a real Kubernetes API server:
```
python3 main.py --kubeconfig '/path/to/your/kube/conf' --address ":8080"
```

To execute unit tests:
```
python3 tests.py -v
```

### Application Usage Guide
**Task #1:**
As an SRE I want to know whether all the deployments in the k8s cluster have as many healthy pods as requested by the respective `Deployment` spec

**Solution #1:** 
Following endpoints have been developed to get the status of Pod/Replicas count
```commandline
GET http://localhost:8080/deployments/status
GET http://localhost:8080/deployments/status?namespace=nsdev
```

**Task #2:**
As an SRE I want to prevent two workloads defined by k8s namespace(s) and label selectors from being able to exchange any network activity on demand

**Solution #2:**
Network traffic have been blocked using Calico Custom CRD Resource
*There are 4 endpoints to create/update/delete/get the network policy*

POST method can be used with input JSON containing source/target namespaces and labels

```commandline
POST http://localhost:8080/networkpolicy
PATCH http://localhost:8080/networkpolicy
DELETE http://localhost:8080/networkpolicy

GET http://localhost:8080/networkpolicies
```
Sample JSON Payload:
```commandline
{
"action": "Deny",
"source_namespace": "nsdev",
"source_app_label": "busybox-dev",
"target_namespace": "nsprod",
"target_app_label": "busybox-prod",
"name": "deny-policy-v1"
}
```

**Task #3:**
As an SRE I want to always know whether this tool can successfully communicate with the configured k8s API server

**Solution #3:**
Following endpoint can be used to get 'ping' status as well as other components health
```commandline
GET http://localhost:8080/k8s/api/health
```

**Task #4:**
As an application developer I want to build this application into a container image when I push a commit to the `main` branch of its repository

**Solution #4:**
Please refer .github/worklflows/build-tyk-image.yaml

**Task #5:**
As an application developer I want to be able to deploy this application into a Kubernetes cluster using Helm

**Solution #5:**
Please refer folder - ./helm-chart