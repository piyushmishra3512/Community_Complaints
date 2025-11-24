#!/usr/bin/env python3
"""Management script for small tasks (local development).

Usage:
  python manage.py set-admin-password <password>

This will create or update a `.env` file in the project root and set ADMIN_PASSWORD.
"""
import argparse
import os
from dotenv import load_dotenv, set_key, find_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, '.env')

load_dotenv(ENV_PATH)

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(dest='command')

set_pwd = subparsers.add_parser('set-admin-password', help='Set ADMIN_PASSWORD in .env')
set_pwd.add_argument('password', help='New admin password')

args = parser.parse_args()

if args.command == 'set-admin-password':
    pwd = args.password
    # ensure .env exists
    if not os.path.exists(ENV_PATH):
        open(ENV_PATH, 'a').close()
    # use dotenv.set_key to update or add the key
    ret = set_key(ENV_PATH, 'ADMIN_PASSWORD', pwd)
    if ret[0] is None:
        print('Failed to update .env')
    else:
        print('ADMIN_PASSWORD updated in', ENV_PATH)
else:
    parser.print_help()
