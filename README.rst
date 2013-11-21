pelix-ecf-chat
##############

Simple chat client and server based on Pelix remote services, that mimics the
ECF Chat demo (https://github.com/ECF/Chat).
This is the base project to implement ECF providers for Pelix
(see https://bugs.eclipse.org/bugs/show_bug.cgi?id=421558).

Requirements
************

This projects is based on Pelix/iPOPO, that can be installed using:

.. code-block:: bash

   sudo pip-3 install iPOPO


It also requires ``jsonrpclib-pelix`` for the remote services part:

.. code-block:: bash

   sudo pip-3 install jsonrpclib-pelix


This project uses random TCP (HTTP) ports, and the Remote Services discovery
service is (for now) using UDP port 42000, in multicast.
Let your firewall open for tests (an argument to define those ports will come
soon).


Finally, the mDNS discovery (work in progress), is based on ``pyzeroconf``
by Mike C. Fletcher, at https://github.com/mcfletch/pyzeroconf.
This library adds support for Zeroconf in Python 2 (not Python 3).

.. code-block:: bash

   $ wget https://github.com/mcfletch/pyzeroconf/archive/master.zip
   $ unzip master.zip
   $ cd pyzeroconf-master
   $ sudo python setup.py install


Server
******

Run the main script with the ``--server`` argument.

.. code-block:: python
   
   python3 main.py --server
   

Client
******

Run the main script with the ``--name`` argument.

.. code-block:: python

   python3 main.py --name Tom

   
You can then use the ``post`` chat command to talk to other clients :

.. code-block:: bash

   $ post Hello, World !
   > Tom: Hello, World !
