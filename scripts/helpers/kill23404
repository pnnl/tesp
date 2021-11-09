#!/bin/bash

lsof -i tcp:23404 | awk 'NR!=1 {print $2}' | xargs kill

