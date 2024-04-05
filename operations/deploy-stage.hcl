job "onionperf-anon-stage" {
  datacenters = ["ator-fin"]
  type        = "service"
  namespace   = "ator-network"

  group "onionperf-anon-stage-group" {
    count = 3

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
    }

    task "onionperf-anon-stage-task" {
      driver = "docker"


      config {
        image   = "svforte/onionperf-anon:latest-stage"
        force_pull = true
      }

      resources {
        cpu    = 512
        memory = 512
      }
    }
  }
}
