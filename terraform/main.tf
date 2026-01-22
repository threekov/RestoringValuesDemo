terraform {
  required_providers {
    openstack = {
      source = "terraform-provider-openstack/openstack"
    }
  }
}

provider "openstack" {
  auth_url    = var.auth_url
  tenant_name = var.tenant_name
  user_name   = var.user_name
  password    = var.password
}

resource "openstack_compute_keypair_v2" "threekov" {
  name       = "threekov"
  public_key = var.public_ssh_key
}

resource "openstack_compute_instance_v2" "knn_vm" {
  name        = "knn-vm-${var.environment}"
  image_name  = var.image_name
  flavor_name = var.flavor_name
  key_pair    = openstack_compute_keypair_v2.threekov.name

  network {
    name = var.network_name
  }
}
