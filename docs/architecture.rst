============
Architecture
============


Overview
========

Architecture overview::

   ┌────────────────┬─────────────────────────────────────────────────────────────┐
   │Clients \o/     │StreamSteam on AWS                                           │
   ├────────────────┼───────────────┬────────────────────────────┬────────────────┤
   │                │         Engine│        ┌────────────┐      │         Modules│
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




Engine
======

The engine is the heart of StreamSteam.

Deployed as a `CloudFormation Stack <https://github.com/ierror/stream-steam/blob/develop/engine/stack.py>`_ it contains all necessary resources to receive events,
enrich them and store in the `S3 Datalake`_.

API Gateway
-----------

Receives events via HTTP(S) and forwards them to a `Lambda`_ for enrichment.

Lambda
------

Enrich events and forwards them to the `Kines Firehose Event Compressor`_

Kines Firehose Event Compressor
-------------------------------

Combines single events into a compressed gz file and stores them in the `S3 Datalake`_.

S3 Datalake
-----------

The data storage for events and artifacts required for deployment.

Structure:

- `events/enriched/` Target prefix for enriched events writtem by the `Kines Firehose Event Compressor`_
- `tmp/` Temp storage for deployment artifacts etc.

Athena / Glue
-------------

Glue Maintains the event schema and Athena allows to query the `S3 Datalake`_ by using SQL.

Event Receivers
---------------

StreamSteam is delivered with a Matomo compatible event receiver.
You can develop your own event receiver. For this purpose the Matomo receiver can be used as a template.

Matomo Event Receiver
+++++++++++++++++++++

The receiver consists of the following components:

- `HTTP Path to map events to a Lambda function <https://github.com/ierror/stream-steam/blob/develop/engine/stack.py#L428>`_
- `Event schema <https://github.com/ierror/stream-steam/blob/develop/engine/matomo_event_receiver/schema.py>`_
- `Lambda function <https://github.com/ierror/stream-steam/blob/develop/engine/matomo_event_receiver/lambda.py>`_
- `Glue Table <https://github.com/ierror/stream-steam/blob/develop/engine/stack.py#L570>`_

Clients
=======

StreamSteam is delivered with Matomo compatible clients to collect events.

* :doc:`web <../clients>`
* :doc:`iOS <../clients>`
* :doc:`Android <../clients>`

Modules
=======

Modules provide the possibility to extend StreamSteam.

Two :doc:`Modules <../modules>` are currently shipped with StreamSteam. Own modules can be created.

* :doc:`Redash EC2 Instance <../modules>`
* :doc:`EMR Spark Cluster <../modules>`


