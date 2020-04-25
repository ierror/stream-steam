.. StreamSteam documentation master file, created by
   sphinx-quickstart on Tue Apr 21 10:44:18 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


======================================
Scalable and Hackable Analytics on AWS
======================================

::

     ______                     ______
    / __/ /________ ___ ___ _  / __/ /____ ___ ___ _
   _\ \/ __/ __/ -_) _ `/  ' \_\ \/ __/ -_) _ `/  ' \
  /___/\__/_/  \__/\_,_/_/_/_/___/\__/\__/\_,_/_/_/_/


StreamSteam is a framework for creating event based near real-time analytics pipelines on AWS.
Installed and configured in minutes, yet extensible and scalable.

Architecture overview::

   ┌────────────────┬─────────────────────────────────────────────────────────────┐
   │Clients \o/     │StreamSteam on AWS                                           │
   ├────────────────┼───────────────┬────────────────────────────┬────────────────┤
   │                │    Core engine│        ┌────────────┐      │         Modules│
   │                ├───────────────┘        │            │      ├────────────────┤
   │                │                        ▼            │      │ ┌────────────┐ │
   │  ┌──────────┐  │      ┌────────┐   ┌────────┐        │      │ │ Spark data │ │
   │  │  Matomo  │  │      │  API   │   │   S3   │        └──────┼─│ processing │ │
   │  │compatible│──┼─┬───▶│Gateway │   │Datalake│◀┐             │ └────────────┘ │
   │  │ clients  │  │ │    └────────┘   └────────┘ │ ┌────────┐  │ ┌────────────┐ │
   │  └──────────┘  │ │         │            ▲     │ │Athena /│  │ │   Redash   │ │
   │  ┌──────────┐  │ │         ▼            │     └─│  Glue  │◀─┼─│ Dashboards │ │
   │  │  Custom  │  │ │    ┌────────┐   ┌────────┐   └────────┘  │ └────────────┘ │
   │  │  Event   │──┼─┘    │ Lambda │   │ Kines  │               │ ┌────────────┐ │
   │  │  types   │  │      │        │──▶│Firehose│               │ │   Custom   │ │
   │  └──────────┘  │      └────────┘   └────────┘               │ │  Modules   │ │
   │                │                                            │ └────────────┘ │
   └────────────────┴────────────────────────────────────────────┴────────────────┘



.. toctree::
   :maxdepth: 2
   :caption: Contents:

   get_started

