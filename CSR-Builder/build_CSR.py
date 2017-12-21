#!/usr/bin/env python

import xlrd
import yaml
import json
from jinja2 import Template
import os

def start_xls(hostname, sheet_id):
	# reads the contents of an excel file and builds dictionaries that are then rendered in a yaml format
	# ensures the paths for placing the cfg and yml files exists
	check_path()
	#opens the excel sheet
	#sheet id 0 is the common information
	#sheet id 1 is the vlan information
	ipam_book = xlrd.open_workbook("CSR_worksheet.xlsx")
	ipam_sheet_common = ipam_book.sheet_by_index(0)
	ipam_sheet_vlan = ipam_book.sheet_by_index(1)

	#creates yaml file
	yml_file_name = hostname + '.yml'
	out_file = open("./yml_files/" + yml_file_name, 'a')

	items = {}
	items['hostname'] = hostname

	for row in range(ipam_sheet_common.nrows):
		#iterates through common information sheet to parse variables
		for column in range(ipam_sheet_common.ncols):
			if ipam_sheet_common.cell_value(row,column) == "Domain Name":
				domain = ipam_sheet_common.cell_value(row,1)
				items['domain_name'] = domain
				#yaml.safe_dump(items, out_file, default_flow_style=False)
			elif ipam_sheet_common.cell_value(row,column) == "Syslog":
				syslog = ipam_sheet_common.cell_value(row,1)
				syslog_servers = [syslog]
				items['syslog_ip'] = syslog_servers
				#yaml.safe_dump(items, out_file, default_flow_style=False)
			elif ipam_sheet_common.cell_value(row,column) == "Netflow":
				netflow = ipam_sheet_common.cell_value(row,1)
				items['netflow_ip'] = netflow
				#yaml.safe_dump(items, out_file, default_flow_style=False)
			elif ipam_sheet_common.cell_value(row,column) == "NTP":
				netflow = ipam_sheet_common.cell_value(row,1)
				items['ntp_ip'] = netflow
				#yaml.safe_dump(items, out_file, default_flow_style=False)
			elif ipam_sheet_common.cell_value(row,column) == "Time Zone":
				time_zone_value = ipam_sheet_common.cell_value(row,1)
				items['time_zone'] = time_zone_value
				#yaml.safe_dump(items, out_file, default_flow_style=False)
			elif ipam_sheet_common.cell_value(row,column) == "SNMP Server":
				SNMP_ip = ipam_sheet_common.cell_value(row,1)
				try:
					SNMP_list
					SNMP_list.extend([SNMP_ip])
				except NameError:
					SNMP_list = [SNMP_ip]
				items['SNMP'] = SNMP_list
				#yaml.safe_dump(items, out_file, default_flow_style=False)
			elif ipam_sheet_common.cell_value(row,column) == "SNMP RO":
				RO_string = ipam_sheet_common.cell_value(row,1)
				try:
					SNMP_RO_list
					SNMP_RO_list.extend([RO_string])
				except NameError:
					SNMP_RO_list = [RO_string]
				items['snmp_community'] = SNMP_RO_list
				#yaml.safe_dump(items, out_file, default_flow_style=False)
			elif ipam_sheet_common.cell_value(row,column) == "SNMP RW":
				RW_string = ipam_sheet_common.cell_value(row,1)
				items['SNMP_RW'] = RW_string
				#yaml.safe_dump(items, out_file, default_flow_style=False)
			elif ipam_sheet_common.cell_value(row,column) == "OSPF Process ID":
				OSPF_string = ipam_sheet_common.cell_value(row,1)
				items['OSPF_Process_ID'] = int(OSPF_string)
				#yaml.safe_dump(items, out_file, default_flow_style=False)
			elif ipam_sheet_common.cell_value(row,column) == "router-id":
				OSPF_Router_ID = ipam_sheet_common.cell_value(row,1)
				items['OSPF_Router_ID'] = OSPF_Router_ID
				#yaml.safe_dump(items, out_file, default_flow_style=False)

	#iterates through the sheet for each switch as defines by separate sheets.
	#populates interface variables for each switch
	ipam_sheet_intf = ipam_book.sheet_by_index(sheet_id)
	for row in range(ipam_sheet_intf.nrows):
		intf_id = ipam_sheet_intf.cell_value(row, 0)
		ip_addr = ipam_sheet_intf.cell_value(row, 1)
		mask = ipam_sheet_intf.cell_value(row,2)
		intf_descr = ipam_sheet_intf.cell_value(row, 3)
		sw_mode = ipam_sheet_intf.cell_value(row,4)
		ospf_area = ipam_sheet_intf.cell_value(row,5)
		if sw_mode == 'L3':
			try:
				intf_info = {}
				intf_info["intf"] = intf_id
				intf_info["description"] = intf_descr
				intf_info["ip"] = ip_addr
				intf_info["mask"] = mask
				intf_info["ospf_area"] = int(ospf_area)
				intf_info["state"] = "no shutdown"
				try:
					intf_list
					intf_list.extend([intf_info])
				except NameError:
					intf_list = [intf_info]
				items['interfaces'] = intf_list
			except ValueError:
				pass
	#prints yaml files, comment out to remove
	print yaml.safe_dump(items, default_flow_style=None, explicit_start=True)
	#writes the items to the yaml file
	yaml.safe_dump(items, out_file, default_flow_style=None, explicit_start=True)
	#calls the config render function, which converts the yaml file, via a jinja2 template, to a Nexus configuration file.
	#passes the yaml file name to be used as the config file name
	config_render(yml_file_name)

def config_render(yml_file):
	#this function opens a yaml file and renders a nexus configuration via a pre-define jinja2 template
	# Parse the YAML file and produce a Python dict.
	yaml_vars = yaml.load(open("./yml_files/" + yml_file).read())
	# Load the Jinja2 template into a Python data structure.
	template = Template(open('CSR.j2').read())
	# Render the configuration using the Jinja2 render method using yaml_vars as arg.
	rendered_config = template.render(yaml_vars)
	# Write the rendered configuration to a text file. Takes the yaml file name strips off the filetype .yml and replaces with .cfg
	name_split = yml_file.split(".")[0]
	config_name = "./cfg_files/" + name_split + ".cfg"
	with open(config_name, 'w') as config:
		config.write(rendered_config)
	if os.path.isfile(config_name):
		print "The configuration file, %s, is present." % config_name
	else:
		print "The configuration file, %s,  is not present." % config_name

def check_path():
	# Creates two directories for placing yaml and config files respectively
	path_yml = "./yml_files/"
	path_cfg = "./cfg_files/"
	paths = [path_yml, path_cfg]
	for path in paths:
		dir = os.path.dirname(path)
		if not os.path.exists(dir):
			os.makedirs(dir)
	return

def build_config():
	# Starting on the third sheet of the workbook, there are the interface attributes.
	# This function iterates through those sheets and uses the sheet name as the switch name.
	# It then passes the hostname and sheet number to the start_xls function, which builds a yaml file.
	ipam_book = xlrd.open_workbook("CSR_worksheet.xlsx")
	num_sheets = len(ipam_book.sheet_names())
	for sheet_id in range(1, num_sheets):
		hostname = ipam_book.sheet_names()[sheet_id]
		start_xls(hostname, sheet_id)

if __name__ == "__main__":
	build_config()
