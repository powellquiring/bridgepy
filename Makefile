FUNCTION_NAMESPACE=pquiring_dev
all: prereq tfinit tfa tst

zip:
	rm python.zip; cd src; zip -r ../python.zip *.py bridgepy/*.py

prereq:
	terraform -version > /dev/null
	terraform -version | grep 'Terraform v0.12'
	terraform -version | grep provider.ibm

prereqfnnamespace:
	ibmcloud --version > /dev/null
	source local.env echo ; ibmcloud fn namespace get $$FUNCTION_NAMESPACE > /dev/null

tfinit:
	terraform init

terraform.tfvars: local.env
	source local.env ; > $@
	source local.env; echo function_namespace='"'$$FUNCTION_NAMESPACE'"' >> $@
	source local.env; echo function_package='"'$$FUNCTION_PACKAGE'"' >> $@
	source local.env; echo function_action='"'$$FUNCTION_ACTION'"' >> $@
	source local.env; echo cos_bucket='"'$$COS_BUCKET'"' >> $@
	source local.env; echo cos_instance='"'$$COS_INSTANCE'"' >> $@
	source local.env; echo ibmcloud_api_key='"'$$IBMCLOUD_API_KEY'"' >> $@

tfa: terraform.tfvars zip
	terraform apply -auto-approve

tfd: terraform.tfvars
	terraform destroy -auto-approve

tfrm:
	rm -rf .terraform terraform.tfstate*

tst:
	source local.env ; url=https://us-south.functions.cloud.ibm.com/api/v1/web/$$FUNCTION_NAMESPACE/$$FUNCTION_PACKAGE/$$FUNCTION_ACTION; echo $$url; curl $$url

venv:
	python3 -m venv venv --prompt bridgepy
	pip install -r requirements.txt

# eval $(make export)
export:
	@echo export BRIDGEPY_COS_INSTANCE_ID=$$(terraform output cos_instance_id) ';'
	@echo export BRIDGEPY_COS_SERVICE_ENDPOINT=$$(terraform output cos_service_endpoint) ';'
	@source local.env; echo export BRIDGEPY_API_KEY=$$IBMCLOUD_API_KEY ';'
	@source local.env; echo export BRIDGEPY_ROOT=$$COS_BUCKET 
	@source local.env; echo export BRIDGEPY_ROOT_TEST=$$COS_BUCKET-test

# make env; then past the results into an "env": X vscode variable in launch.json to configure the debugger
env:
	@ eval $$(make export) ; echo '{"BRIDGEPY_COS_INSTANCE_ID": "'$$BRIDGEPY_COS_INSTANCE_ID'",' \
		'"BRIDGEPY_COS_SERVICE_ENDPOINT": "'$$BRIDGEPY_COS_SERVICE_ENDPOINT'",' \
		'"BRIDGEPY_API_KEY": "'$$BRIDGEPY_API_KEY'",' \
		'"BRIDGEPY_ROOT": "'$$BRIDGEPY_ROOT'",' \
		'"BRIDGEPY_ROOT_TEST": "'$$BRIDGEPY_ROOT_TEST'"}' \
		 | jq .

fastapi:
	cd src; uvicorn bridgepy.fast:app --reload

mypy:
	cd src; mypy bridgepy/cli.py

requirements.txt:
	pip freeze --exclude-editable | sed s/=.*// > requirements.txt
