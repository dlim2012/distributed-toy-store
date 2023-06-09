# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: order.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0border.proto\x12\x05unary\"7\n\rorder_details\x12\x14\n\x0cproduct_name\x18\x01 \x01(\t\x12\x10\n\x08quantity\x18\x02 \x01(\x05\"#\n\x0border_query\x12\x14\n\x0corder_number\x18\x01 \x01(\x05\"\x1b\n\x04ping\x12\x13\n\x0bping_number\x18\x01 \x01(\x05\"Q\n\x11order_information\x12\x14\n\x0corder_number\x18\x01 \x01(\x05\x12\x14\n\x0cproduct_name\x18\x02 \x01(\t\x12\x10\n\x08quantity\x18\x03 \x01(\x05\x32\xc9\x01\n\x05Order\x12\x31\n\x03\x42uy\x12\x14.unary.order_details\x1a\x12.unary.order_query\"\x00\x12\x33\n\x05\x43heck\x12\x12.unary.order_query\x1a\x14.unary.order_details\"\x00\x12\"\n\x04Ping\x12\x0b.unary.ping\x1a\x0b.unary.ping\"\x00\x12\x34\n\tPropagate\x12\x18.unary.order_information\x1a\x0b.unary.ping\"\x00\x62\x06proto3')



_ORDER_DETAILS = DESCRIPTOR.message_types_by_name['order_details']
_ORDER_QUERY = DESCRIPTOR.message_types_by_name['order_query']
_PING = DESCRIPTOR.message_types_by_name['ping']
_ORDER_INFORMATION = DESCRIPTOR.message_types_by_name['order_information']
order_details = _reflection.GeneratedProtocolMessageType('order_details', (_message.Message,), {
  'DESCRIPTOR' : _ORDER_DETAILS,
  '__module__' : 'order_pb2'
  # @@protoc_insertion_point(class_scope:unary.order_details)
  })
_sym_db.RegisterMessage(order_details)

order_query = _reflection.GeneratedProtocolMessageType('order_query', (_message.Message,), {
  'DESCRIPTOR' : _ORDER_QUERY,
  '__module__' : 'order_pb2'
  # @@protoc_insertion_point(class_scope:unary.order_query)
  })
_sym_db.RegisterMessage(order_query)

ping = _reflection.GeneratedProtocolMessageType('ping', (_message.Message,), {
  'DESCRIPTOR' : _PING,
  '__module__' : 'order_pb2'
  # @@protoc_insertion_point(class_scope:unary.ping)
  })
_sym_db.RegisterMessage(ping)

order_information = _reflection.GeneratedProtocolMessageType('order_information', (_message.Message,), {
  'DESCRIPTOR' : _ORDER_INFORMATION,
  '__module__' : 'order_pb2'
  # @@protoc_insertion_point(class_scope:unary.order_information)
  })
_sym_db.RegisterMessage(order_information)

_ORDER = DESCRIPTOR.services_by_name['Order']
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  _ORDER_DETAILS._serialized_start=22
  _ORDER_DETAILS._serialized_end=77
  _ORDER_QUERY._serialized_start=79
  _ORDER_QUERY._serialized_end=114
  _PING._serialized_start=116
  _PING._serialized_end=143
  _ORDER_INFORMATION._serialized_start=145
  _ORDER_INFORMATION._serialized_end=226
  _ORDER._serialized_start=229
  _ORDER._serialized_end=430
# @@protoc_insertion_point(module_scope)