job "onionperf-anon-live" {
  datacenters = ["ator-fin"]
  type        = "service"
  namespace   = "ator-network"

  group "onionperf-anon-live-group" {
    count = 3

    volume "onionperf-data" {
      type      = "host"
      read_only = false
      source    = "onionperf-live"
    }

    spread {
      attribute = "${node.unique.id}"
      weight    = 100
      target "c8e55509-a756-0aa7-563b-9665aa4915ab" {
        percent = 34
      }
      target "c2adc610-6316-cd9d-c678-cda4b0080b52" {
        percent = 33
      }
      target "4aa61f61-893a-baf4-541b-870e99ac4839" {
        percent = 33
      }
    }

    network {
      mode = "bridge"

      port "http-port" {
        static = 9222
        to     = 80
      }
    }

    task "onionperf-anon-live-task" {
      driver = "docker"

      volume_mount {
        volume      = "onionperf-data"
        destination = "/home/onionperf/onionperf-data"
        read_only   = false
      }

      config {
        image   = "svforte/onionperf-anon:latest-live"
        volumes = ["local/anonrc:/etc/anon/anonrc:ro"]
        force_pull = true
      }

      service {
        name = "onionperf-anon-live"
        tags = [ "logging" ]
      }

      resources {
        cpu    = 256
        memory = 256
      }
      
      template {
        change_mode = "noop"
        data        = <<EOH
AgreeToTerms 1        
        EOH
        destination = "local/anonrc"
      }
    }

    task "onionperf-nginx-live-task" {
      driver = "docker"

      volume_mount {
        volume      = "onionperf-data"
        destination = "/var/www/onionperf-data"
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
        cpu    = 64
        memory = 64
      }

      service {
        name     = "onionperf-live"
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

  root /var/www/onionperf-data/htdocs;

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
