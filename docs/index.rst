.. StreamSteam documentation master file, created by
   sphinx-quickstart on Tue Apr 21 10:44:18 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


====================================================
StreamSteam - Scalable and Hackable Analytics on AWS
====================================================

StreamSteam is a framework for creating event based near real-time analytics pipelines on AWS.
Installed and configured in minutes, yet extensible and scalable.

Walkthrough
===========

.. raw:: html

   <iframe id="walkthrough" width="600" height="450" src="https://www.youtube.com/embed/Z8YgLPXMyhA" frameborder="0" allow="accelerometer; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>


Chapters
--------

0. `Setup <https://www.youtube.com/watch?v=Z8YgLPXMyhA>`_
1. `Deployment <https://www.youtube.com/watch?v=Z8YgLPXMyhA&t=1m30s>`_
2. `Web Tracking Client to create example events <https://www.youtube.com/watch?v=Z8YgLPXMyhA&t=3m30s>`_
3. `How to use the redash module <https://www.youtube.com/watch?v=Z8YgLPXMyhA&t=06m00s>`_
4. `How to use the EMR Spark Cluster module <https://www.youtube.com/watch?v=Z8YgLPXMyhA&t=15m00s>`_
5. `Destroy the Stack <https://www.youtube.com/watch?v=Z8YgLPXMyhA&t=20m30s>`_


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
   :maxdepth: 3

   get_started
   modules
