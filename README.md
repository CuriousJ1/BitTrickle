# BitTrickle: A Permissioned Peer-to-Peer File Sharing System

This project implements BitTrickle, a permissioned peer-to-peer file sharing system with a centralised indexing server. The system combines client-server and peer-to-peer models, consisting of one server and multiple clients. Here’s how it works:

##Features
###Server Responsibilities:
- Authenticate users joining the peer-to-peer network.
- Maintain a record of files stored by users.
- Facilitate file searches and connect users for direct file transfers.

###Client Capabilities:
- Join the peer-to-peer network through a command-line interface.
- Share files with the network.
- Search for and retrieve files from other users.
  
##Communication Protocols
- Client-Server Communication: All interactions between clients and the server occur over UDP.
- Peer-to-Peer Communication: File transfers between clients occur over TCP.

This system demonstrates key concepts in distributed systems, including authentication, indexing, and protocol-specific communication models.
