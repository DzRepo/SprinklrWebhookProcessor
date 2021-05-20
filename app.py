"""
Case Message Parser - capture webhook from Sprinklr to parse out webform values, updating Case fields with the form
values.
"""
import os
import requests
import json
from flask import Flask, render_template
from flask import request, jsonify, Response
from bs4 import BeautifulSoup
import SprinklrClient as Sprinklr
from google.cloud import logging, secretmanager
import datetime

# Custom Field IDs - use custom field search API to retrieve ( https://developer.sprinklr.com/docs/read/api_10/custom_fields/Custom_Field_Search )
email_address_id        = "_c_6063639c75f96d01204dd2b2"       
request_type_id         = "_c_60467545be45773ee8218568"       
social_account_id       = "_c_6052e6d2d149063797dba0f8"       
blog_channel_id         = "_c_60467d0abe45773ee8231d95"       
title_id                = "_c_6063382deb4ffc5a236f3c19"       
link_to_draft_id        = "_c_60467f8fbe45773ee8238d2a"       
link_to_asset_id        = "_c_60467feabe45773ee8239ea1"       
publish_date_id         = "_c_60468073be45773ee823b909"       
publish_time_id         = "_c_604680e0be45773ee823cd32"       
priority_id             = "_c_6046813fbe45773ee823e184"       
special_instructions_id = "_c_6063385ceb4ffc5a236f5421" 

# Build the parent name from the project.
project_id = "casewebhooklistener"
parent = f"projects/{project_id}"

def access_secret(secret_id, version_id="latest"):
    # Create the Secret Manager client.
    secret_client = secretmanager.SecretManagerServiceClient()
    # Build the resource name of the secret version.
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    # Access the secret version.
    response = secret_client.access_secret_version(name=name)
    # Return the decoded payload.
    return response.payload.data.decode('UTF-8')
    
# Sprinklr Access Token and API Key are stored in Google Secrets repository.
access_token = access_secret("AccessToken")
key = access_secret("APIKey")

env = None # Only set if not using Production environment.
sprinklr_client = Sprinklr.SprinklrClient(key, env, access_token)

# pylint: disable=C0103
app = Flask(__name__)

def get_form_text(label):
    global soup
    header = soup.find('td', text=label)
    if header is not None:
        # if it's an href, return the link text, otherwise, just return the text
        if header.find_next_sibling('td').text is None:
            return header.find_next_sibling('td').contents[0]
        return header.find_next_sibling('td').text
    else:
        return None

soup = None

@app.route('/', methods=['POST'])
def process_post():
    global soup
    logging_client = logging.Client()
    log_name = "posted-data"
    logger = logging_client.logger(log_name)

    case_object = request.json
    logger.log_text("POST received")
    logger.log_struct(case_object)
    
    if "payload" in case_object:
        if "description" in case_object["payload"]:
            form_data = case_object["payload"]["description"]
            case_number = case_object["payload"]["caseNumber"]
            if form_data is not None:

                # More precise validation could be done here - such as looking for specific form ID.
                if "Webform Response to:Acme Social Request Demo" in form_data:
                    soup            = BeautifulSoup(form_data, "html.parser")
                    email           = get_form_text("Email Address")
                    how_help        = get_form_text("How can we help?")
                    which_social    = get_form_text("Which Social Account should be used if any?")
                    blog_channel    = get_form_text("Select a Blog Channel")
                    title           = get_form_text("Title")
                    link_to_draft   = get_form_text("Link to draft")
                    link_to_asset   = get_form_text("Link to Asset")
                    publish_date    = get_form_text("Preferred Publish Date")
                    publish_time    = get_form_text("Preferred Publish Time (PST)")
                    priority        = get_form_text("Priority")
                    instructions    = get_form_text("Special Instructions")

                    # Build Update Case Request Object                    
                    request_json = {
                        "updateActions": [
                        "SYNC_SELECTED_PROPERTIES"
                        ],
                        "caseNumbers": [
                            case_number
                        ],
                        "syncedSelectedCustomProperties": {
                            title_id: [
                                title
                            ],
                            email_address_id: [
                                email
                            ],
                            request_type_id: [
                                how_help
                            ],
                            social_account_id: [
                                which_social
                            ],
                            blog_channel_id: [
                                blog_channel
                            ],
                            link_to_draft_id: [
                                link_to_draft
                            ],
                            link_to_asset_id: [
                                link_to_asset
                            ],
                            publish_date_id: [
                                publish_date + " " + publish_time + " GMT"
                            ],
                            publish_time_id: [
                                publish_time
                            ],
                            priority_id: [
                                priority
                            ],
                            special_instructions_id:[
                                instructions
                            ]
                        }
                    }

                    # Log Request Object (for debugging)
                    logger.log_struct(request_json)

                    # Make update request to Sprinklr. Returns true if successful.
                    if sprinklr_client.update_case(request_json):
                        logger.log_text("case " + str(case_number) + " updated.")
                    else:
                        logger.log_text("Error updating case: " + sprinklr_client.result)
                else:
                    logger.log_text("Not a webform. Skipping")
            else:
                logger.log_text("form_data is None")
        else:
            logger.log_text("Description not found in Payload")
    else:
        logger.log_text("Payload not found in jsonPayload")

    return Response("", status=200)

if __name__ == '__main__':
    server_port = os.environ.get('PORT', '8080')
    app.run(debug=False, port=server_port, host='0.0.0.0')