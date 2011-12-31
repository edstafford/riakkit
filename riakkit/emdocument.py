# This file is part of RiakKit.
#
# RiakKit is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# RiakKit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with RiakKit.  If not, see <http://www.gnu.org/licenses/>.

from riakkit.exceptions import *
from riakkit.types import BaseProperty, LinkedDocuments, ReferenceProperty, MultiReferenceProperty
from riakkit.utils import *

class EmDocumentMetaclass(type):
  """Meta class that the EmDocuments class is made from."""
  def __new__(cls, clsname, parents, attrs):
    if clsname == "EmDocument":
      return type.__new__(cls, clsname, parents, attrs)

    meta = {}
    hasdefaults = {}
    references = {}

    for name in attrs.keys():
      # No LinkedDocuments, ReferenceProperties only work with NON-Embedded
      # Documents. collection_name does not work either!
      if isinstance(attrs[name], (ReferenceProperty, MultiReferenceProperty)):
        references[name] = prop = attrs.pop(name)
      elif isinstance(attrs[name], BaseProperty) and not isinstance(attrs[name], LinkedDocuments):
        meta[name] = prop = attrs.pop(name)
        if prop.default is not None:
          hasdefaults[name] = prop.defaultValue()

    all_parents = reversed(walkParents(parents, ("EmDocument", "object", "type")))
    for p_cls in all_parents:
      p_meta = copy(p_cls._meta) # Shallow copy should be ok.
      p_references = p_meta.pop("_references")
      meta.update(p_meta)
      references.update(p_references)
      hasdefaults.update(p_cls._hasdefaults)

    meta["_references"] = references
    attrs["_meta"] = meta
    attrs["_hasdefaults"] = hasdefaults
    return type.__new__(cls, clsname, parents, attrs)

class EmDocument(dict):
  """The base Embedded Document class for embedded documents to extend from.

  EmDocument (Embedded document) is a Document like class that could be embedded
  into documents. This extends both from the dict type.

  EmDocument should be able to embed EmDocument as well. When saved to the
  database, EmDocument becomes a dictionary.

  EmDocument is not similar to Document and it has a lot of limitations. First
  off, there is no unique checking, there is not LinkedDocuments and for
  ReferenceBaseProperty, there's no collection_name AND there's no linking to
  other EmDocument. EmDocument doesn't have all the APIs of Document. It's more
  like a fancy DictProperty with type conversion and checking. No keys, either.
  """

  __metaclass__ = EmDocumentMetaclass

  def _error(self, name):
    raise AttributeError("Attribute %s not found with %s." %
        (name, self.__class__.__name__))

  def __getitem__(self, name):
    inMeta = name in self._meta
    inData = name in self

    if not inMeta and inData:
      return dict.__getitem__(self, name)

    if inMeta and not inData:
      return None

    if inMeta and inData:
      return dict.__getitem__(self, name)

    if not inMeta and not inData:
      self._error(name)

  def __setitem__(self, name, value):
    validator = lambda x: True
    standardizer = lambda x: x
    if name in self._meta:
      validator = self._meta[name].validate
      standardizer = self._meta[name].standardize
    elif name in self._meta["_references"]:
      validator = self._meta["_references"][name].validate
      standardizer = self._meta["_references"][name].standardize

    if not validator(value):
      raise ValueError("Validation did not pass for %s for the field %s.%s" % (value, self.__class__.__name__, name))
    value = standardizer(value)
    self.__setitem__(name, value)

  __getattr__ = __getitem__
  __setattr__ = __setitem__
  __delattr__ = dict.__delitem__