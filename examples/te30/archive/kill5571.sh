lsof -i tcp:5571 | awk 'NR!=1 {print $2}' | xargs kill

