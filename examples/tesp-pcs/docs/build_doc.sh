rm -r ./build/* && \
sphinx-build -b html -Ea ./source ./build/ 
# && \
# sphinx-build -b latex ./source -Ea ./build/ && \
# cd ./build/ && make clean && make