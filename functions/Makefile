FUNCTION_NAMESPACE=pquiring_dev
all: zip tfa test

zip:
	rm python.zip; cd ../src; zip -r ../functions/python.zip *.py bridgepy/*.py

prereq:
	echo check function namespace $(FUNCTION_NAMESPACE) ; ic fn namespace get $(FUNCTION_NAMESPACE)

tfa: prereq zip
	terraform apply -auto-approve

tst:
	curl https://us-south.functions.cloud.ibm.com/api/v1/web/pquiring_dev/$$(terraform output name)/$$(terraform output name)

