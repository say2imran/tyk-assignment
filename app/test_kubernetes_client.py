from kubernetes import client, config

if __name__ == '__main__':
    kube_config = '/var/snap/microk8s/current/credentials/client.config'
    config.load_kube_config(kube_config)
    kube_api_client = client.CoreV1Api()
    print("Listing pods with their IPs:")
    pods = kube_api_client.list_pod_for_all_namespaces(watch=False)
    for pod in pods.items:
        print("%s\t%s\t%s" % (pod.status.pod_ip, pod.metadata.namespace, pod.metadata.name))

    kube_api_client = client.AppsV1Api()
    deployments = kube_api_client.list_deployment_for_all_namespaces()
    for deployment in deployments.items:
        if deployment.metadata.name != 'mynginx':
            continue
        print(deployment)
        print("---------------------------")
        print("Deployment Name | Expected Replicas | Unavailable Replicas")
        print(deployment.metadata.name + " | " + str(deployment.status.replicas) + " | " + str(deployment.status.unavailable_replicas))
        print(deployment.metadata.name, deployment.status)
        print("=================================")
