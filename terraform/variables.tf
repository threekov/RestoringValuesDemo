variable "auth_url" {}
variable "tenant_name" {}
variable "user_name" {}
variable "password" {}

variable "image_name" {
  default = "ubuntu-22.04"
}

variable "flavor_name" {
  default = "m1.small"
}

variable "network_name" {
  default = "sutdents-net"
}

variable "public_ssh_key" {}

variable "environment" {
  default = "demo"
}
