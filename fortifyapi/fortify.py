#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "Brandon Spruth (brandon.spruth2@target.com), Jim Nelson (jim.nelson2@target.com)"
__copyright__ = "(C) 2017 Target Brands, Inc."
__contributors__ = ["Brandon Spruth", "Jim Nelson", "Matthew Dunaj"]
__status__ = "Production"
__license__ = "MIT"

import urllib
import urllib3
import json
import ntpath
import requests
import requests.auth
import requests.exceptions
import requests.packages.urllib3
from . import __version__ as version


class FortifyApi(object):
    def __init__(self, host, username=None, password=None, token=None, verify_ssl=True, timeout=60, user_agent=None,
                 client_version='17.10.0158'):

        self.host = host
        self.username = username
        self.password = password
        self.token = token
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.client_version = client_version

        if not user_agent:
            self.user_agent = 'fortify_api/' + version
        else:
            self.user_agent = user_agent

        if not self.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Set auth_type based on what's been provided
        if username is not None:
            self.auth_type = 'basic'
        elif token is not None:
            self.auth_type = 'token'
        else:
            self.auth_type = 'unauthenticated'

    def bulk_create_new_application_version_request(self, version_id, development_phase, development_strategy,
                                                    accessibility, business_risk_ranking, custom_attribute=('', '')):
        """
        Creates a new Application Version by using the Bulk Request API. 'create_new_project_version' must be used
        before calling this method.
        :param version_id: Version ID
        :param development_phase: Development Phase GUID of Version
        :param development_strategy: Development Strategy GUID of Version
        :param accessibility: Accessibility GUID of Version
        :param business_risk_ranking: Business Risk Rank GUID of Version
        :param custom_attribute: Custom Attribute tuple that consists of attributeDefinitionId & Value. Default is a
                                 empty string tuple.
        :return: A response object containing the newly created project and project version
        """
        data = self._bulk_format_new_application_version_payload(version_id=version_id,
                                                                 development_phase=development_phase,
                                                                 development_strategy=development_strategy,
                                                                 accessibility=accessibility,
                                                                 business_risk_ranking=business_risk_ranking,
                                                                 custom_attribute=custom_attribute)
        url = '/ssc/api/v1/bulk'
        return self._request('POST', url, data=data)

    @staticmethod
    def _bulk_format_attribute_definition(attribute_definition_id_value, guid_value='', value='null'):
        json_application_version = dict(attributeDefinitionId=attribute_definition_id_value,
                                        values=[],
                                        value=value)
        if guid_value is not None:
            json_application_version['values'] = [dict(guid=guid_value)]
        return json_application_version

    def _bulk_format_new_application_version_payload(self, version_id, development_phase, development_strategy,
                                                     accessibility, business_risk_ranking, custom_attribute):
        json_application_version = dict(requests=[
            self._bulk_create_attributes(version_id, development_phase, development_strategy, accessibility,
                                         business_risk_ranking, custom_attribute),
            self._bulk_create_responsibilities(version_id),
            self._bulk_create_configurations(version_id),
            self._bulk_create_commit(version_id),
            self._bulk_create_version(version_id)
        ])
        return json.dumps(json_application_version)

    def _bulk_create_attributes(self, version_id, development_phase, development_strategy,
                                accessibility, business_risk_ranking, custom_attribute):
        if business_risk_ranking is None:
            business_risk_ranking = 'High'
        json_application_version = dict(
            uri=self.host + '/ssc/api/v1/projectVersions/' + str(version_id) + '/attributes',
            httpVerb='PUT',
            postData=[
                self._bulk_format_attribute_definition('5', development_phase),
                self._bulk_format_attribute_definition('6', development_strategy),
                self._bulk_format_attribute_definition('7', accessibility),
                self._bulk_format_attribute_definition('1', business_risk_ranking),
            ])

        if custom_attribute[0] is not '' and custom_attribute[1] is not '':
            json_application_version['postData'].append(

                self._bulk_format_attribute_definition(attribute_definition_id_value=custom_attribute[0],
                                                       value=custom_attribute[1]))

        return json_application_version

    def _bulk_create_responsibilities(self, version_id):
        json_application_version = dict(
            uri=self.host + '/ssc/api/v1/projectVersions/' + str(version_id) + '/responsibilities',
            httpVerb='PUT',
            postData=[]
        )
        json_application_version['postData'] = [dict(responsibilityGuid='projectmanager',
                                                     userId='null'),
                                                dict(responsibilityGuid='securitychampion',
                                                     userId='null'),
                                                dict(responsibilityGuid='developmentmanager',
                                                     userId='null'),
                                                ]
        return json_application_version

    def _bulk_create_configurations(self, version_id):
        json_application_version = dict(uri=self.host + '/ssc/api/v1/projectVersions/' + str(version_id) + '/action',
                                        httpVerb='POST',
                                        postData=[dict(
                                            type='COPY_FROM_PARTIAL',
                                            values={
                                                "projectVersionId": str(version_id),
                                                "previousProjectVersionId": '-1',
                                                "copyAnalysisProcessingRules": 'true',
                                                "copyBugTrackerConfiguration": 'true',
                                                "copyCurrentStateFpr": 'false',
                                                "copyCustomTags": 'true'
                                            }
                                        )]
                                        )
        return json_application_version

    def _bulk_create_commit(self, version_id):
        json_application_version = dict(
            uri=self.host + '/ssc/api/v1/projectVersions/' + str(version_id),
            httpVerb='PUT',
            postData={
                "committed": 'true'
            }
        )
        return json_application_version

    def _bulk_create_version(self, version_id):
        json_application_version = dict(uri=self.host + '/ssc/api/v1/projectVersions/' + str(version_id) + '/action',
                                        httpVerb='POST',
                                        postData=[dict(
                                            type='COPY_CURRENT_STATE',
                                            values={
                                                "projectVersionId": str(version_id),
                                                "previousProjectVersionId": '-1',
                                                "copyCurrentStateFpr": 'false'
                                            }
                                        )]
                                        )
        return json_application_version

    def create_application_version(self, application_name, application_template, version_name, description,
                                   application_id=None):
        """
        :param application_name: Project name
        :param application_id: Project ID
        :param application_template: Application template name
        :param version_name: Version name
        :param description: Application Version description
        :return: A response object containing the created project version
        """
        # If no application ID is given, sets JSON value to null.
        if application_id is None:
            application_id = 'null'

        # Gets Template ID
        issue_template = self.get_issue_template_id(project_template_name=application_template)
        issue_template_id = issue_template.data['data'][0]['id']

        json_application_version = dict(name=version_name,
                                        description=description,
                                        active=True,
                                        committed=False,
                                        project={
                                            'name': application_name,
                                            'description': description,
                                            'issueTemplateId': issue_template_id,
                                            'id': application_id
                                        },
                                        issueTemplateId=issue_template_id)

        data = json.dumps(json_application_version)
        url = '/ssc/api/v1/projectVersions'
        return self._request('POST', url, data=data)

    def download_artifact(self, artifact_id):
        """
        You might use this method like this, for example
            api = FortifyApi("https://my-fortify-server:my-port", token=get_token())
            response, file_name = api.download_artifact_scan("my-id")
            if response.success:
                file_content = response.data
                with open('/path/to/some/folder/' + file_name, 'wb') as f:
                    f.write(file_content)
            else:
                print response.message

        We've coded this for the entire file to load into memory. A future change may be to permit
        streaming/chunking of the file and handing back a stream instead of content.
        :param artifact_id: the id of the artifact to download
        :return: binary file data and file name
        """
        file_token = self.get_file_token('DOWNLOAD').data['data']['token']

        url = "/ssc/download/artifactDownload.html?mat=" + file_token + "&id=" + str(
            artifact_id) + "&clientVersion=" + self.client_version

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }

        response = self._request('GET', url, stream=True, headers=headers)

        try:
            file_name = response.headers['Content-Disposition'].split('=')[1].strip("\"'")
        except:
            file_name = ''

        return response, file_name

    def download_artifact_scan(self, artifact_id):
        """
        You might use this method like this, for example
            api = FortifyApi("https://my-fortify-server:my-port", token=get_token())
            response, file_name = api.download_artifact_scan("my-id")
            if response.success:
                file_content = response.data
                with open('/path/to/some/folder/' + file_name, 'wb') as f:
                    f.write(file_content)
            else:
                print response.message

        We've coded this for the entire file to load into memory. A future change may be to permit
        streaming/chunking of the file and handing back a stream instead of content.
        :param artifact_id: the id of the artifact scan to download
        :return: binary file data and file name
        """
        file_token = self.get_file_token('DOWNLOAD').data['data']['token']

        url = "/ssc/download/currentStateFprDownload.html?mat=" + file_token + "&id=" + str(
            artifact_id) + "&clientVersion=" + self.client_version + "&includeSource=true"

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }

        response = self._request('GET', url, stream=True, headers=headers)

        try:
            file_name = response.headers['Content-Disposition'].split('=')[1].strip("\"'")
        except:
            file_name = ''

        return response, file_name

    def get_artifact_scans(self, parent_id):
        """
        :param parent_id: parent resource identifier
        :return: A response object containing artifact scans
        """
        url = "/ssc/api/v1/artifacts/" + str(parent_id) + "/scans"
        return self._request('GET', url)

    def get_attribute_definition(self, search_expression):
        """
        :param search_expression: A fortify-formatted search expression, e.g. Development Phase
        :return: A response object containing the result of the GET
        """
        if search_expression:
            url = '/ssc/api/v1/attributeDefinitions?q=name:"' + search_expression + '"'
            return self._request('GET', url)
        else:
            return FortifyResponse(message='A search expression must be provided', success=False)

    def get_attribute_definitions(self):
        """
        :return: A response object containing all attribute definitions
        """
        url = '/ssc/api/v1/attributeDefinitions?start=-1&limit=-1'
        return self._request('GET', url)

    def get_cloudscan_jobs(self):
        """
        :return: A response object containing all cloudscan jobs
        """
        url = '/ssc/api/v1/cloudjobs?start=-1&limit=-1'
        return self._request('GET', url)

    def get_cloudscan_job_status(self, scan_id):
        """
        :return: A response object containing a cloudscan job
        """
        url = '/ssc/api/v1/cloudjobs/' + scan_id
        return self._request('GET', url)

    def get_file_token(self, purpose):
        """
        :param purpose: specify if the token is for file 'UPLOAD' or 'DOWNLOAD'
        :return: a response body containing a file token for the specified purpose
        """

        url = "/ssc/api/v1/fileTokens"
        if purpose == 'UPLOAD':
            data = json.dumps(
                {
                    "fileTokenType": "UPLOAD"
                }
            )
        elif purpose == 'DOWNLOAD':
            data = json.dumps(
                {
                    "fileTokenType": "DOWNLOAD"
                }
            )
        else:
            return FortifyResponse(message='attribute purpose must be either UPLOAD or DOWNLOAD', success=False)

        return self._request('POST', url, data=data)

    def get_issue_template(self, project_template_id):
        """
        :param project_template_id: id of project template
        :return: A response object with data containing issue templates for the supplied project name
        """

        url = "/ssc/api/v1/issueTemplates" + "?limit=1&q=id:\"" + project_template_id + "\""
        return self._request('GET', url)

    def get_issue_template_id(self, project_template_name):
        """
        :param project_template_name: name of project template
        :return: A response object with data containing issue templates for the supplied project name
        """

        url = "/ssc/api/v1/issueTemplates" + "?limit=1&fields=id&q=name:\"" + project_template_name + "\""
        return self._request('GET', url)

    def get_project_version_artifacts(self, parent_id):
        """
        :param parent_id: parent resource identifier
        :return: A response object containing project version artifacts
        """
        url = "/ssc/api/v1/projectVersions/" + str(parent_id) + "/artifacts?start=-1&limit=-1"
        return self._request('GET', url)

    def get_project_version_attributes(self, project_version_id):
        """
        :param project_version_id: Project version id
        :return: A response object containing the project version attributes
        """
        url = '/ssc/api/v1/projectVersions/' + str(project_version_id) + '/attributes/?start=-1&limit=-1'
        return self._request('GET', url)

    def get_all_project_versions(self):
        """
        :return: A response object with data containing project versions
        """
        url = "/ssc/api/v1/projectVersions?start=-1&limit=-1"
        return self._request('GET', url)

    def get_project_versions(self, project_name):
        """
        :return: A response object with data containing project versions
        """

        url = "/ssc/api/v1/projectVersions?limit=0&q=project.name:\"" + project_name + "\""
        return self._request('GET', url)

    def get_projects(self):
        """
        :return: A response object with data containing projects
        """

        url = "/ssc/api/v1/projects?start=-1&limit=-1"
        return self._request('GET', url)

    def get_token(self):
        """
        :return: A response object with data containing create date, terminal date, and the actual token
        """

        data = {
            "type": "UnifiedLoginToken"
        }

        data = json.dumps(data)
        url = '/ssc/api/v1/tokens'
        return self._request('POST', url, data=data)

    def post_attribute_definition(self, attribute_definition):
        """
        :param attribute_definition:
        :return:
        """
        url = '/ssc/api/v1/attributeDefinitions'
        data = json.dumps(attribute_definition)
        return self._request('POST', url, data=data)

    def upload_artifact_scan(self, file_path, project_version_id):
        """
        :param file_path: full path to the file to upload
        :param project_version_id: project_version_id
        :return: Response from the file upload operation
        """
        upload = self.get_file_token('UPLOAD')
        if upload is None or upload.data['data'] is None:
            return FortifyResponse(message='Failed to get the SSC upload file token', success=False)

        file_token = upload.data['data']['token']
        url = "/ssc/upload/resultFileUpload.html?mat=" + file_token
        files = {'file': (ntpath.basename(file_path), open(file_path, 'rb'))}

        headers = {
            'Accept': 'Accept:application/xml, text/xml, */*; q=0.01',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }

        params = {
            'entityId': project_version_id,
            'clientVersion': self.client_version,
            'Upload': "Submit Query",
            'Filename': ntpath.basename(file_path)
        }

        return self._request('POST', url, params, files=files, stream=True, headers=headers)

    def _request(self, method, url, params=None, files=None, data=None, headers=None, stream=False):
        """Common handler for all HTTP requests."""
        if not params:
            params = {}

        if not headers:
            headers = {
                'Accept': 'application/json'
            }
            if method == 'GET' or method == 'POST' or method == 'PUT':
                headers.update({'Content-Type': 'application/json'})
        headers.update({'User-Agent': self.user_agent})

        try:

            if self.auth_type == 'basic':
                response = requests.request(method=method, url=self.host + url, params=params, files=files,
                                            headers=headers, data=data,
                                            timeout=self.timeout, verify=self.verify_ssl,
                                            auth=(self.username, self.password), stream=stream)
            elif self.auth_type == 'token':
                response = requests.request(method=method, url=self.host + url, params=params, files=files,
                                            headers=headers, data=data,
                                            timeout=self.timeout, verify=self.verify_ssl,
                                            auth=FortifyTokenAuth(self.token), stream=stream)
            else:
                response = requests.request(method=method, url=self.host + url, params=params, files=files,
                                            headers=headers, data=data,
                                            timeout=self.timeout, verify=self.verify_ssl, stream=stream)

            try:
                response.raise_for_status()

                # two flavors of response are successful, GETs return 200, PUTs return 204 with empty response text
                response_code = response.status_code
                success = True if response_code // 100 == 2 else False
                if response.text:
                    try:
                        data = response.json()
                    except ValueError:  # Sometimes the returned data isn't JSON, so return raw
                        data = response.content

                return FortifyResponse(success=success, response_code=response_code, data=data,
                                       headers=response.headers)
            except ValueError as e:
                return FortifyResponse(success=False, message="JSON response could not be decoded {0}.".format(e))
        except requests.exceptions.SSLError as e:
            return FortifyResponse(message='An SSL error occurred. {0}'.format(e), success=False)
        except requests.exceptions.ConnectionError as e:
            return FortifyResponse(message='A connection error occurred. {0}'.format(e), success=False)
        except requests.exceptions.Timeout:
            return FortifyResponse(message='The request timed out after ' + str(self.timeout) + ' seconds.',
                                   success=False)
        except requests.exceptions.RequestException as e:
            return FortifyResponse(
                message='There was an error while handling the request. {0}'.format(e), success=False)


class FortifyTokenAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers['Authorization'] = 'FortifyToken ' + self.token
        return r


class FortifyResponse(object):
    """Container for all Fortify SSC API responses, even errors."""

    def __init__(self, success, message='OK', response_code=-1, data=None, headers=None):
        self.message = message
        self.success = success
        self.response_code = response_code
        self.data = data
        self.headers = headers

    def __str__(self):
        if self.data:
            return str(self.data)
        else:
            return self.message

    def data_json(self, pretty=False):
        """Returns the data as a valid JSON string."""
        if pretty:
            return json.dumps(self.data, sort_keys=True, indent=4, separators=(',', ': '))
        else:
            return json.dumps(self.data)
