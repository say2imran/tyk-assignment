import socketserver

from kubernetes import client, config
from http.server import BaseHTTPRequestHandler
from prettytable import PrettyTable
from urllib.parse import urlparse, parse_qs
import json
import os


class AppHandler(BaseHTTPRequestHandler):
    def __init__(self, kube_config, *args, **kwargs):
        self.kube_config = kube_config
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Catch all incoming GET requests"""

        # Parse URL to get query variable if any
        seperator = self.path.find('?')
        url_path = self.path[:seperator] if seperator != -1 else self.path
        query_vars = parse_qs(urlparse(self.path).query)

        if self.path == "/healthz":
            self.healthz()

        elif url_path == "/deployments/status":
            # If namespace has been providedin the query string, then use it to filter deployments
            if query_vars.get('namespace'):
                self.deployment_status(query_vars.get('namespace')[0])
            else:
                self.deployment_status()

        elif url_path == "/networkpolicies":
            self.get_network_polices()

        elif url_path == "/k8s/api/health":
            self.kubernetes_api_server_health_status()
        else:
            self.send_error(404)

    def do_POST(self):
        '''Reads post request body'''
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        try:
            user_data = json.loads(post_data)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        if self.path == "/networkpolicy":
            self.create_network_policy(user_data)
        else:
            self.send_error(404)

    def do_DELETE(self):
        '''Reads post request body'''
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        try:
            user_data = json.loads(post_data)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        if self.path == "/networkpolicy":
            self.delete_network_policy(user_data)
        else:
            self.send_error(404)

    def do_PATCH(self):
        '''Reads post request body'''
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        print("print patch data")
        print(post_data)

        try:
            user_data = json.loads(post_data)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        if self.path == "/networkpolicy":
            self.update_network_policy(user_data)
        else:
            self.send_error(404)

    def healthz(self):
        """Responds with the health status of the application"""
        self.respond(200, "ok")

    def respond(self, status: int, content: str):
        """Writes content and status code to the response socket"""
        self.send_response(status)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()

        self.wfile.write(bytes(content, "UTF-8"))

    def deployment_status(self, namespace=None):
        """Responds with the status of the deployment"""
        config.load_kube_config(self.kube_config)
        kube_api_client = client.AppsV1Api()
        print(namespace)
        if namespace is None:
            deployments = kube_api_client.list_deployment_for_all_namespaces()
        else:
            deployments = kube_api_client.list_namespaced_deployment(namespace)

        table = PrettyTable(['Deployment Name', 'Expected Replicas', 'Ready Replicas', 'Unavailable Replicas'])
        for deployment in deployments.items:
            table.add_row([deployment.metadata.name, deployment.status.replicas, deployment.status.ready_replicas,
                           deployment.status.unavailable_replicas])

        self.respond(200, table.get_string())

    def get_network_polices(self):
        config.load_kube_config(self.kube_config)
        kube_api_client_custom = client.CustomObjectsApi()
        custom_policies = kube_api_client_custom.list_cluster_custom_object(
            group="crd.projectcalico.org",
            version="v1",
            plural="networkpolicies",
        )
        self.respond(200, str(custom_policies))

    def create_network_policy(self, user_data):
        calico_policy = read_calico_policy_json_file()
        # Updating Source/Target Namespace/Labels in Calico policy json
        calico_policy['metadata']['name'] = user_data['name']
        calico_policy['metadata']['namespace'] = user_data['target_namespace']
        calico_policy['spec']['selector'] = f"app == '{user_data['target_app_label']}'"

        calico_policy["spec"]["ingress"][0]["action"] = user_data["action"]
        calico_policy["spec"]["ingress"][0]["source"]["namespaceSelector"] = f"app == '{user_data['source_namespace']}'"
        calico_policy["spec"]["ingress"][0]["source"]["selector"] = f"app == '{user_data['source_app_label']}'"

        calico_policy["spec"]["egress"][0]["action"] = user_data["action"]
        calico_policy["spec"]["egress"][0]["destination"][
            "namespaceSelector"] = f"app == '{user_data['target_namespace']}'"
        calico_policy["spec"]["egress"][0]["destination"]["selector"] = f"app == '{user_data['target_app_label']}'"
        # pprint.pprint(calico_policy)

        kube_api_client = client.CustomObjectsApi()
        print("INFO: Creating resource")
        try:
            api_response = kube_api_client.create_namespaced_custom_object(
                group="crd.projectcalico.org",
                version="v1",
                namespace=user_data['target_namespace'],
                plural="networkpolicies",
                body=calico_policy,
                pretty=True
            )
            self.respond(201, "Resource created")
        except client.exceptions.ApiException as e:
            self.respond(e.status, e.body)
        print("INFO: Done with policy creation")

    def update_network_policy(self, user_data):
        print("INFO: Updating network policy")

        calico_policy = read_calico_policy_json_file()

        # Updating Source/Target Namespace/Labels in Calico policy json
        print("INFO: Creating Calico Policy")
        calico_policy['metadata']['name'] = user_data['name']
        calico_policy['metadata']['namespace'] = user_data['target_namespace']
        calico_policy['spec']['selector'] = f"app == '{user_data['target_app_label']}'"

        calico_policy["spec"]["ingress"][0]["action"] = user_data["action"]
        calico_policy["spec"]["ingress"][0]["source"]["namespaceSelector"] = f"app == '{user_data['source_namespace']}'"
        calico_policy["spec"]["ingress"][0]["source"]["selector"] = f"app == '{user_data['source_app_label']}'"

        calico_policy["spec"]["egress"][0]["action"] = user_data["action"]
        calico_policy["spec"]["egress"][0]["destination"][
            "namespaceSelector"] = f"app == '{user_data['target_namespace']}'"
        calico_policy["spec"]["egress"][0]["destination"]["selector"] = f"app == '{user_data['target_app_label']}'"

        print("INFO: Calico Policy", calico_policy)
        kube_api_client = client.CustomObjectsApi()

        try:
            api_response = kube_api_client.patch_namespaced_custom_object(
                group="crd.projectcalico.org",
                version="v1",
                namespace=user_data['target_namespace'],
                plural="networkpolicies",
                body=calico_policy,
                name=user_data['name']
            )
            self.respond(200, "Resource Updated")
        except client.exceptions.ApiException as e:
            print("Exception when calling CustomObjectsApi->patch_namespaced_custom_object: %s\n" % e)
            self.respond(e.status, e.body)

        print("INFO: Done with policy update")

    def delete_network_policy(self, user_data):
        print("INFO: Deleting network policy")
        kube_api_client = client.CustomObjectsApi()
        try:
            api_response = kube_api_client.delete_namespaced_custom_object(
                group="crd.projectcalico.org",
                version="v1",
                namespace=user_data['target_namespace'],
                plural="networkpolicies",
                body=client.V1DeleteOptions(),
                name=user_data['name']
                #grace_period_seconds = 1
                #propagation_policy = 'propagation_policy_example' # str | Whether and how garbage collection will be performed. Either this field or OrphanDependents may be set, but not both. The default policy is decided by the existing finalizer set in the metadata.finalizers and the resource-specific default policy. (optional)

            )
            self.respond(200, "Resource Deleted")
        except client.exceptions.ApiException as e:
            self.respond(e.status, e.body)
        print("INFO: Done with policy deletion")

    def kubernetes_api_server_health_status(self):
        """Responds with the status of the Kubernetes API server"""
        config.load_kube_config(self.kube_config)
        kube_api_client = client.ApiClient()

        try:
            health_response = kube_api_client.call_api(resource_path="/healthz",
                                                       method="GET",
                                                       query_params={"verbose": "true"},
                                                       response_type='str',
                                                       _return_http_data_only=False,
                                                       header_params={"Accept": "application/json"},
                                                       collection_formats=dict(fields=None))

            self.respond(health_response[1], str(health_response[0]))

        except client.exceptions.ApiException as e:
            self.respond(e.status, e.body)


def read_calico_policy_json_file():
    cwd = os.getcwd()
    policy_json_file = os.path.join(cwd, 'crd_policies/calico/v1_calico_deny_ns_label.json')
    with open(policy_json_file) as f:
        return json.load(f)


def get_kubernetes_version(api_client: client.ApiClient) -> str:
    """
    Returns a string GitVersion of the Kubernetes server defined by the api_client.

    If it can't connect an underlying exception will be thrown.
    """
    version = client.VersionApi(api_client).get_code()
    return version.git_version


def start_server(address, kube_config):
    """
    Launches an HTTP server with handlers defined by AppHandler class and blocks until it's terminated.

    Expects an address in the format of `host:port` to bind to.

    Throws an underlying exception in case of error.
    """
    try:
        host, port = address.split(":")
    except ValueError:
        print("invalid server address format")
        return

    with socketserver.TCPServer((host, int(port)),
                                lambda *args, **kwargs: AppHandler(kube_config, *args, **kwargs)) as httpd:
        print("Server listening on {}".format(address))
        httpd.serve_forever()
