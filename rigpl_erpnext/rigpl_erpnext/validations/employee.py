# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe, re
from frappe import _
from rigpl_erpnext.rigpl_erpnext.validations.lead import \
	create_new_user_perm, delete_unused_perm, find_total_perms
from frappe import msgprint
from frappe.utils import getdate
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time

def validate(doc,method):
	#Validation for Age of Employee should be Greater than 18 years at the time of Joining.
	dob = getdate(doc.date_of_birth)
	doj = getdate(doc.date_of_joining)
	if relativedelta(doj, dob).years < 18:
		frappe.msgprint("Not Allowed to Create Employees under 18 years of Age", raise_exception = 1)
	if doc.relieving_date:
		if doc.status != "Left":
			frappe.msgprint("Status has to be 'LEFT' as the Relieving Date is populated",raise_exception =1)
		else:
			doc.leave_approvers = []
			doc.reports_to = ''
	
	doc.employee_number = doc.name
	doc.employee = doc.name
	if doc.aadhaar_number:
		validate_aadhaar(doc.aadhaar_number)
	if doc.pan_number:
		validate_pan(doc.pan_number)

def on_update(doc,method):
	allowed_ids = []
	for la in doc.leave_approvers:
		if la.leave_approver:
			allowed_ids.extend([la.leave_approver])
			create_new_user_perm(doc.doctype, doc.name, la.leave_approver)

	if doc.reports_to:
		reports_to_userid = frappe.db.get_value("Employee", doc.reports_to, "user_id")
		if reports_to_userid:
			allowed_ids.extend([reports_to_userid])
			create_new_user_perm(doc.doctype, doc.name, reports_to_userid)

	if doc.user_id:
		allowed_ids.extend([doc.user_id])
		create_new_user_perm(doc.doctype, doc.name, doc.user_id)

	total_perms = find_total_perms(doc.doctype, doc.name)

	if total_perms:
		for extra in total_perms:
			if extra[2] in allowed_ids:
				pass
			else:
				delete_unused_perm(extra[0], doc.doctype, doc.name, extra[2])

def validate_pan(pan):
	if pan:
		p = re.compile("[A-Z]{5}[0-9]{4}[A-Z]{1}")
		if not p.match(pan):
			frappe.throw(_("Invalid PAN Number or Enter NA for Unknown"))

def validate_aadhaar(aadhaar):
	if aadhaar:
		p = re.compile("[0-9]{12}")
	if not p.match(aadhaar):
		frappe.throw(_("Invalid Aadhaar Number"))
	aadhaar_check_digit = calcsum(aadhaar[:-1])
	if aadhaar[-1:] != str(aadhaar_check_digit):
		frappe.throw(_("Invalid Aadhaar Number"))

verhoeff_table_d = (
    (0,1,2,3,4,5,6,7,8,9),
    (1,2,3,4,0,6,7,8,9,5),
    (2,3,4,0,1,7,8,9,5,6),
    (3,4,0,1,2,8,9,5,6,7),
    (4,0,1,2,3,9,5,6,7,8),
    (5,9,8,7,6,0,4,3,2,1),
    (6,5,9,8,7,1,0,4,3,2),
    (7,6,5,9,8,2,1,0,4,3),
    (8,7,6,5,9,3,2,1,0,4),
    (9,8,7,6,5,4,3,2,1,0))

verhoeff_table_p = (
    (0,1,2,3,4,5,6,7,8,9),
    (1,5,7,6,2,8,3,0,9,4),
    (5,8,0,3,7,9,6,1,4,2),
    (8,9,1,6,0,4,3,5,2,7),
    (9,4,5,3,1,2,6,8,7,0),
    (4,2,8,6,5,7,3,9,0,1),
    (2,7,9,3,8,0,6,4,1,5),
    (7,0,4,6,9,1,3,2,5,8))

verhoeff_table_inv = (0,4,3,2,1,5,6,7,8,9)

def calcsum(number):
    """For a given number returns a Verhoeff checksum digit"""
    c = 0
    for i, item in enumerate(reversed(str(number))):
        c = verhoeff_table_d[c][verhoeff_table_p[(i+1)%8][int(item)]]
    return verhoeff_table_inv[c]
	
def autoname(doc,method):
	doj = getdate(doc.date_of_joining)
	id = frappe.db.sql("""SELECT current FROM `tabSeries` WHERE name = '%s'""" %doc.naming_series, as_list=1)
	id = str(id[0][0])
	#Generate employee number on the following logic
	#Employee Number would be YYYYMMDDXXXXC, where:
	#YYYYMMDD = Date of Joining in YYYYMMDD format
	#XXXX = Serial Number of the employee from the ID this is NUMBERIC only
	#C= Check DIGIT
	if doc.date_of_joining:
		doj = str(doj.year) + str(doj.month).zfill(2)
		code = doj+id
		check = fn_check_digit(doc, code)
		code = code + str(check)
	doc.name = code

	
###############~Code to generate the CHECK DIGIT~###############################
#Link: https://wiki.openmrs.org/display/docs/Check+Digit+Algorithm
################################################################################
def fn_check_digit(doc,id_without_check):

	# allowable characters within identifier
	valid_chars = "0123456789ABCDEFGHJKLMNPQRSTUVYWXZ"

	# remove leading or trailing whitespace, convert to uppercase
	id_without_checkdigit = id_without_check.strip().upper()

	# this will be a running total
	sum = 0;

	# loop through digits from right to left
	for n, char in enumerate(reversed(id_without_checkdigit)):

			if not valid_chars.count(char):
					raise Exception('InvalidIDException')

			# our "digit" is calculated using ASCII value - 48
			digit = ord(char) - 48

			# weight will be the current digit's contribution to
			# the running total
			weight = None
			if (n % 2 == 0):

					# for alternating digits starting with the rightmost, we
					# use our formula this is the same as multiplying x 2 &
					# adding digits together for values 0 to 9.  Using the
					# following formula allows us to gracefully calculate a
					# weight for non-numeric "digits" as well (from their
					# ASCII value - 48).
					weight = (2 * digit) - int((digit / 5)) * 9
			else:
					# even-positioned digits just contribute their ascii
					# value minus 48
					weight = digit

			# keep a running total of weights
			sum += weight

	# avoid sum less than 10 (if characters below "0" allowed,
	# this could happen)
	sum = abs(sum) + 10

	# check digit is amount needed to reach next number
	# divisible by ten. Return an integer
	return int((10 - (sum % 10)) % 10)
