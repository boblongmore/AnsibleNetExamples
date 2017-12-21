# CSR Builder
Collect information about how a router is built in an excel file. This file includes basic information such as domain name, NTP, SNMP, etc. This file also includes interface and routing configurations

The script parses the spreadsheet and populates a yaml file. The script then builds a rotuer configuration based on the yaml variables. 

Requires xlrd, yaml, jinja2.
