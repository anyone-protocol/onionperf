job "onionperf-anon-live" {
  datacenters = ["ator-fin"]
  type        = "service"
  namespace   = "ator-network"

  group "onionperf-anon-live-group" {
    count = 3

    volume "onionperf-results" {
      type      = "host"
      read_only = false
      source    = "onionperf-live"
    }

    spread {
      attribute = "${node.unique.id}"
      weight    = 100
      target "067a42a8-d8fe-8b19-5851-43079e0eabb4" {
        percent = 34
      }
      target "16be0723-edc1-83c4-6c02-193d96ec308a" {
        percent = 33
      }
      target "e6e0baed-8402-fd5c-7a15-8dd49e7b60d9" {
        percent = 33
      }
    }

    network {
      mode = "bridge"

      port "connect-port" {
        static = 9520
        host_network = "wireguard"
      }

      port "listen-port" {
        static = 9510
      }

      port "http-port" {
        static = 9222
        to     = 80
        host_network = "wireguard"
      }
    }

    task "onionperf-anon-live-task" {
      driver = "docker"

      volume_mount {
        volume      = "onionperf-results"
        destination = "/home/onionperf/results"
        read_only   = false
      }

      config {
        image   = "svforte/onionperf-anon:latest-live"
        force_pull = true
      }

      service {
        name = "onionperf-anon-live"
        tags = [ "logging" ]
      }

      resources {
        cpu    = 512
        memory = 512
      }
    }

    task "onionperf-nginx-live-task" {
      driver = "docker"

      volume_mount {
        volume      = "onionperf-results"
        destination = "/var/www/onionperf"
        read_only   = true
      }

      config {
        image   = "nginx"
        volumes = [
          "local/nginx-onionperf:/etc/nginx/conf.d/default.conf:ro"
        ]
        ports = ["http-port"]
      }

      resources {
        cpu    = 256
        memory = 256
      }

      service {
        name     = "onionperf-live"
        provider = "nomad"
        tags     = ["onionperf", "logging"]
        port     = "http-port"
        check {
          name     = "onionperf nginx http server alive"
          type     = "tcp"
          interval = "10s"
          timeout  = "10s"
          check_restart {
            limit = 10
            grace = "30s"
          }
        }
      }

      template {
        change_mode = "noop"
        data        = <<EOH
##
# The following is a simple nginx configuration to run OnionPerf.
##
server {

  root /var/www/onionperf;

  # This option make sure that nginx will follow symlinks to the appropriate
  # OnionPerf folders
  autoindex on;

  index index.html;

  listen 0.0.0.0:80;

  location / {
    try_files $uri $uri/ =404;
  }

  location ~/\.ht {
    deny all;
  }
}
        EOH
        destination = "local/nginx-onionperf"
      }
    }
  }
}
