"""Exec the native implementation in the same process to meet the RSS constraint."""
import os
import sys
from ament_index_python.packages import get_package_prefix
os.execv(get_package_prefix('dashboard_tools')+'/lib/dashboard_tools/dashboard_aggregator',['dashboard_aggregator']+sys.argv[1:])
