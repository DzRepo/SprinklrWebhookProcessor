# Sprinklr Webhook Processor

"Sprinklr WebHook Processor" is a small python app that could run as a Google Cloud Run, AWS Lambda or Azure Web Function. It captures a webhook sent from Sprinklr, parses a webform passed as the contents of the (included) first message, and updates both standard and custom fields of the case with the webform values.

It uses the [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) HTML parser and [SprinklrClient](https://github.com/DzRepo/SprinklrClient) to update the Case.