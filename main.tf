variable ibmcloud_api_key {}
variable function_namespace { }
variable function_package { }
variable function_action { }
variable cos_instance { }
variable cos_bucket { }

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


provider ibm {
  region           = "${var.region}"
  function_namespace = "${var.function_namespace}"
  ibmcloud_api_key = "${var.ibmcloud_api_key}"
  ibmcloud_timeout = "${var.ibmcloud_timeout}"
}

resource "ibm_resource_instance" "cos_instance" {
  name              = "${var.cos_instance}"
  service           = "cloud-object-storage"
  plan              = "standard"
  location          = "global"
}

resource "ibm_cos_bucket" "bucket" {
  bucket_name = "${var.cos_bucket}"
  resource_instance_id = "${ibm_resource_instance.cos_instance.id}"
  region_location = "${var.region}"
  storage_class = "standard"
}

resource "ibm_function_package" "package" {
  name = "${var.function_package}"
}

locals {
  function_full_name = "${ibm_function_package.package.name}/${var.function_action}"
}

resource "ibm_function_action" action {
  name = "${local.function_full_name}"

  exec {
    kind = "python:3.7"
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

output cos_instance_id {
  value = "${ibm_resource_instance.cos_instance.id}"
}
output function_full_name {
  value = "${local.function_full_name}"
}
