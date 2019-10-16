import requests                                   # For RESTful calls
from requests.auth import HTTPBasicAuth           # For initial authentication w/ DNAC
requests.packages.urllib3.disable_warnings()      # Disable warnings. Living on the wild side..
import logging.handlers
import argparse
import time

def getToken ():
  # Retrieves an authentication Token from Cisco DNA Center
  # Returns the Token

  url = "https://" + args.dnac_ip + ":" + args.dnac_port + "/api/system/v1/auth/token"
  res = requests.post(url=url, auth=HTTPBasicAuth(args.user, args.password), verify=False)
  return(res.json()['Token'])

def dnacGet (uri):
  # GET API call from Cisco DNA Center (to avoid repetition)

  url = "https://" + args.dnac_ip + ":" + args.dnac_port + uri
  headers = {'Content-Type': "application/json", 'x-auth-token': token}
  body = ""
  res = requests.get(url=url, headers=headers, json=body, verify=False)
  return (res.json()['response'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='cisco-dnac-platform-audit-by-syslog version 1.3.1')
    parser.add_argument('--verbose', action='store_true', help="Vernose mode")
    parser.add_argument('--syslog_ip', help="please enter the IP address of the syslog server")
    parser.add_argument('--syslog_port', help="please enter the UDP of the syslog server, default port is 514", type=int, default=514)
    parser.add_argument('--dnac_ip', help="please enter the IP of the Cisco DNA Center4")
    parser.add_argument('--dnac_port', help="please enter the port of the Cisco DNA Center, default port is 443", type=str, default="443")
    parser.add_argument('--user', help="please enter the username for Cisco DNA Center, default user is admin", default="admin")
    parser.add_argument('--password', help="please enter the password for Cisco DNA Center")
    parser.add_argument('--period', help="please enter the polling period (in minutes), default is 5", type=int, default=5)
    parser.add_argument('--token_refresh', help="please enter the token refresh time (in minutes), default is 50", type=int, default=50)
    args = parser.parse_args()

    # Arguments verification:
    if args.syslog_ip is None:
        raise Exception("Sorry, no syslog server is set")
    if args.dnac_ip is None:
        raise Exception("Sorry, no DNAC IP is set")
    if args.password is None:
        raise Exception("Sorry, no password for DNAC is set")

    # Creating the logger
    dnac_logger = logging.getLogger('dnac_logger')
    dnac_logger.setLevel(logging.INFO)

    #Creating the logging handler, directing to the syslog server
    handler = logging.handlers.SysLogHandler(address = (args.syslog_ip,args.syslog_port))
    dnac_logger.addHandler(handler)

    print("\n ************************************************* \n")
    if args.verbose:
        print(" * Verbose Enabled")
    else:
        print(" * Verbose Disabled")

    lastEventId = ""
    tokenTime = time.time()
    token = getToken()
    if args.verbose:
        print(" * DNAC Token: " + str(token))

# Entering an infinite loop

    while True:

        # Refreshing the DNAC Token every period of time
        if time.time()-tokenTime > args.token_refresh*60:
            token = getToken()
            tokenTime = time.time()
            if args.verbose:
                print(" * DNAC Token: " + str(token))

        # Getting the latest Audit log
        audit = dnacGet("/api/v1/audit?auditParentId=&limit=100&offset=0&orderBy=createdDateTime&orderByType=desc")
        if args.verbose:
            print(audit)
        duplicate = False

        # Going through the events (until we reach the last event of the previous pull)
        for event in audit:
            if event['auditId'] == lastEventId:
                duplicate = True
            elif not duplicate:
                eventTime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(event['createdDateTime']/1000))
                data = "%s | Device %s (%s) | requester: %s | Description: %s" % (eventTime, event['deviceName'], event['deviceIP'], event['auditRequestor'], event['auditDescription'])

                if args.verbose:
                    print(data)

                # Send the event via syslog
                dnac_logger.info(str(data))

        # Mark the newest event as the last one, for the next loop
        lastEventId = audit[0]['auditId']
        if duplicate and args.verbose:
            print("\nreached the last event from the previous poll.")
        print("\nFinished this poll, waiting for the next...")

        # Sleep until next time
        time.sleep(60*args.period)
