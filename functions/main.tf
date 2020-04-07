variable ibmcloud_api_key {}
variable resource_group_name {
  default = "default"
}

variable "ibmcloud_timeout" {
  description = "Timeout for API operations in seconds."
  default     = 900
}

variable region {
  default = "us-south"
}

variable function_namespace {
  default = "pquiring_dev"
}

provider ibm {
  region           = "${var.region}"
  function_namespace = "${var.function_namespace}"
  ibmcloud_api_key = "${var.ibmcloud_api_key}"
  ibmcloud_timeout = "${var.ibmcloud_timeout}"
}

locals {
  prefix = "aaa"
  name = "${local.prefix}-bridgepy"
}

resource "ibm_function_package" "package" {
  name = "${local.name}"
}

resource "ibm_function_action" action {
  name = "${ibm_function_package.package.name}/${local.name}"

  exec {
    kind = "python:3.7"
    // code = "${file("hellopython.py")}"
    code = "${base64encode("${file("python.zip")}")}"
  }
  user_defined_annotations = <<EOF
    [
        {
            "key": "exec",
            "value": "python:3.7"
        },
        {
            "key": "web-export",
            "value": true
        },
        {
            "key": "final",
            "value": true
        }
    ]
EOF
  user_defined_parameters = <<EOF
    [
      {
          "key":"api_key",
          "value":"${var.ibmcloud_api_key}"
      }
    ]
EOF
}

output name {
  value = "${local.name}"
}
