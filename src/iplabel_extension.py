
# use an override of the original Dynatrace API wrapper to let me create a test with no result (only alarms)
from dynatrace_local_override import Dynatrace

from dynatrace.environment_v1.synthetic_third_party import SYNTHETIC_EVENT_TYPE_OUTAGE

from ruxit.api.base_plugin import RemoteBasePlugin
import logging
import json
from datetime import datetime
import requests
from requests import ReadTimeout, ConnectTimeout, HTTPError, Timeout, ConnectionError

log = logging.getLogger(__name__)


class IpLabelExtension(RemoteBasePlugin):
    def initialize(self, **kwargs):
        # The Dynatrace API client
        self.dt_client = Dynatrace(self.config.get("api_url"), self.config.get(
            "api_token"), log=log, proxies=self.build_proxy_url())
        self.executions = 0
        self.failures_detected = 0

    def build_proxy_url(self):
        proxy_address = self.config.get("proxy_address")
        proxy_username = self.config.get("proxy_username")
        proxy_password = self.config.get("proxy_password")

        if proxy_address:
            protocol, address = proxy_address.split("://")
            proxy_url = f"{protocol}://"
            if proxy_username:
                proxy_url += proxy_username
            if proxy_password:
                proxy_url += f":{proxy_password}"
            proxy_url += f"@{address}"
            return {"https": proxy_url}

        return {}

    def query(self, **kwargs) -> None:

        log.setLevel(self.config.get("log_level"))

        frequency = int(self.config.get("frequency")
                        ) if self.config.get("frequency") else 15

        if self.executions % frequency == 0:

            # query IP-Label for the selected scenario
            # get its details and execution results for the spcified time frame
            # get any related alert

            scenarioname = self.config.get("scenario_name")
            domainname = self.config.get("domain_name")
            include_results = self.config.get("include_results")
            test_name = self.config.get("test_name")

            instances = getinstances(domainname, scenarioname)
            log.debug(json.dumps(instances))

            for instance in instances:

                # set default value for response time.
                # if set to None, will not generate step value
                value = None
                # do we want to include response time ?
                if include_results != "None":

                    # get results for this instance
                    results = getresults(domainname, str(instance["Scenario"]["Id"]), str(
                        instance["Robot"]["Id"]), str(frequency))
                    log.debug(json.dumps(results))

                    for result in results:
                        if value is None:
                            value = result["Value"]
                        else:
                            value += result["Value"]

                        # do we want to include response time at step level ?
                        if include_results == "Step Level":

                            details = getresultdetail(
                                domainname, str(result["Id"]))
                            log.debug(json.dumps(details))
                            # TODO: build the detailed results out of this data

                log.info("sending test data with results details : "+include_results)

                the_test_id="iplabel"+str(self.activation.entity_id)+str(instance["Id"])
                the_test_title=test_name+" - "+str(instance["Name"])

                self.dt_client.third_part_synthetic_tests.report_simple_thirdparty_synthetic_test(
                    engine_name="Ip-Label",
                    timestamp=datetime.now(),
                    location_id=str(instance["Robot"]["Id"]),
                    location_name=str(instance["Robot"]["Name"]),
                    test_id=the_test_id,
                    test_title=the_test_title,
                    step_title="Overall",
                    schedule_interval=instance["Frequency"],
                    success=True,
                    response_time=value
                )

                # get alarms
                alarms = getalarms(domainname, str(instance["Id"]), str(frequency))
                log.debug(json.dumps(alarms))
                for alarm in alarms:
                    self.dt_client.third_part_synthetic_tests.report_simple_thirdparty_synthetic_test_event(
                        test_id=the_test_id,
                        name="Ip-Label reported alarm for "+the_test_title,
                        location_id=str(instance["Robot"]["Id"]),
                        timestamp=datetime.now(),
                        state="open" if alarm["HasEnded"] == False else "resolved",
                        event_type=SYNTHETIC_EVENT_TYPE_OUTAGE,
                        reason=alarm["Text"],
                        engine_name="Ip-Label",
                    )
        self.executions += 1

# --------------------------------------------------------------------------------


def getinstances(domain, scenarioname):
    instances = []

    log.debug('http://'+domain+'/rest/api/instances?scenario='+scenarioname)

    try:
        with requests.get(
            'http://'+domain+'/rest/api/instances?scenario='+scenarioname,
            headers={
                'accept': 'application/json'
            },
            verify=False
        ) as ri:

            # error ?
            if(ri.status_code != 200):
                log.error(ri.status_code, ri.reason, ri.text)
                return []

            log.debug(ri.text)
            # parse retrieved data as json
            instances = json.loads(ri.text)
            log.info("Found "+str(len(instances))+" instance(s).")
    except (ConnectTimeout, HTTPError, Timeout, ConnectionError):
        # handle ConnectionError the exception
        log.error("Issue in getting IP-Label instances for scenario " +
                  scenarioname+" on domain "+domain)
    return instances

# --------------------------------------------------------------------------------


def getresults(domain, scenarioid, robotid, timerange):
    results = []

    log.debug('http://'+domain+'/rest/api/results?scenario=' +
              scenarioid+'&robot='+robotid+'&range='+timerange)

    try:
        with requests.get(
            'http://'+domain+'/rest/api/results?scenario=' +
                scenarioid+'&robot='+robotid+'&range='+timerange,
            headers={
                'accept': 'application/json'
            },
            verify=False
        ) as rr:

            # error ?
            if(rr.status_code != 200):
                log.error(rr.status_code, rr.reason, rr.text)
                return []

            log.debug(rr.text)
            # parse retrieved data as json
            results = json.loads(rr.text)
            log.info("Found "+str(len(results))+" result(s).")
    except (ConnectTimeout, HTTPError, Timeout, ConnectionError):
        # handle ConnectionError the exception
        log.error("Issue in getting IP-Label results for scenario " +
                  scenarioid+" and robot "+robotid+" on timerange "+timerange)
    return results

# --------------------------------------------------------------------------------


def getresultdetail(domain, resultid):
    details = []

    log.debug('http://'+domain+'/rest/api/results/'+resultid)

    try:

        with requests.get(
            'http://'+domain+'/rest/api/results/'+resultid,
            headers={
                'accept': 'application/json'
            },
            verify=False
        ) as rd:

            # error ?
            if(rd.status_code != 200):
                log.error(rd.status_code, rd.reason, rd.text)
                return ""

            log.debug(rd.text)
            # parse retrieved data as json
            details = json.loads(rd.text)
            log.info("Found "+str(len(details))+" detail(s).")
    except (ConnectTimeout, HTTPError, Timeout, ConnectionError):
        # handle ConnectionError the exception
        log.error("Issue in getting IP-Label details for result "+resultid)
    return details

# --------------------------------------------------------------------------------


def getalarms(domain, instanceid, timerange):
    alarms = []

    log.debug('http://'+domain+'/rest/api/alarms?source=' +
              instanceid+'&range='+timerange)

    try:

        with requests.get(
            'http://'+domain+'/rest/api/alarms?source='+instanceid+'&range='+timerange,
            headers={
                'accept': 'application/json'
            },
            verify=False
        ) as ra:

            # error ?
            if(ra.status_code != 200):
                log.error(ra.status_code, ra.reason, ra.text)
                return []

            log.debug(ra.text)
            # parse retrieved data as json
            alarms = json.loads(ra.text)
            log.info("Found "+str(len(alarms))+" alarm(s).")
    except (ConnectTimeout, HTTPError, Timeout, ConnectionError):
        # handle ConnectionError the exception
        log.error("Issue in getting IP-Label alarms for instance " +
                  instanceid+" on timerange "+timerange)
    return alarms

# --------------------------------------------------------------------------------
