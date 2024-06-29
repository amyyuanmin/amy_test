import sys
import time
import pytest
import os
import shutil
import xml.etree.cElementTree as ET
import re
import glob
import logging
import subprocess

logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(levelname)s : %(message)s')

def xml_analysis(xml_file):
    '''
    There might be two versions of xml report:
    #1. <testsuites> as root
    #2. <testsuite> as root, i.e. no <testsuites> level
    '''
    logging.info("Analyzing pytest xml report")
    tree = ET.ElementTree(file = xml_file)
    root = tree.getroot()

    # for #2 
    for item in root.attrib:
        if item == "errors":
            if int(root.attrib[item]) !=0:
                logging.error("There are {} errors".format(root.attrib[item]))
                return -1
        elif item == "failures":
            if int(root.attrib[item]) !=0:
                logging.error("There are {} failures".format(root.attrib[item]))
                return -1
    # for #1
    for child in root:
        logging.debug("child.tag {}, child.attrib {}".format(child.tag, child.attrib))
        for item in child.attrib:
            if item == "errors":
                logging.info("error num is {}".format(child.attrib[item]))
                if int(child.attrib[item]) !=0:
                    logging.error("There are errors")
                    return -1
            elif item == "failures":
                logging.info("failures num is {}".format(child.attrib[item]))
                if int(child.attrib[item]) !=0:
                    logging.error("There are failures")
                    return -1
    logging.info("No failure or error found")
    return 0