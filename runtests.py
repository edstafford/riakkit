#!/usr/bin/python

import unittest
import riak
from riakkit import Document, EmDocument
from riakkit.types import *
rc = riak.RiakClient()

def deleteAllKeys(client, bucketname):
  bucket = client.bucket(bucketname)
  keys = bucket.get_keys()
  for key in keys:
    bucket.get(key).delete()

class CustomDocument(Document):
  client = rc

class E(EmDocument):
  name = ListProperty(forwardprocessors=lambda x: [int(i) for i in x])

class A(CustomDocument):
  bucket_name = "test_A"

  n = StringProperty()
  l = ListProperty(forwardprocessors=lambda x: [int(i) for i in x])
  em = EmDocumentsDictProperty(emdocument_class=E)

class B(CustomDocument):
  bucket_name = "test_B"

  someA = DictReferenceProperty(reference_class=A)

class ClassPage(CustomDocument):
  bucket_name = "test_class"

  name = StringProperty()

class SomeUser(CustomDocument):
  bucket_name = "test_someuser"

  page = ReferenceProperty(reference_class=ClassPage, collection_name="users")
  name = StringProperty()

class UniqueTest(CustomDocument):
  bucket_name = "test_unique"

  attr = StringProperty(unique=True)

class All(unittest.TestCase):
  def test_referenceModifiedOnSave(self):
    a = A(l=["1", "2", "3"], em={"a" : {"name" : ["1", "2", "3"]}})
    a.save()
    self.assertEqual(["1", "2", "3"], a.l)
    self.assertEqual(["1", "2", "3"], a.em["a"].name)

  def test_setUpdictRefProperty(self):
    a = A(n="a")
    a.save()
    c = A(n="c")
    b = B(someA={"a" : a, "c" : c})
    b.save()
    b.reload()
    self.assertEqual(b.someA["a"], a)
    self.assertEqual(b.someA["c"], c)

  def test_uniqueAttributesSetup(self):
    # Testing changing unique attribute
    unique = UniqueTest(attr="test")
    unique.save()
    unique.attr = "non-test"
    unique.save()
    unique.attr = "test"
    unique.save()

    # Test double saving
    unique.save()

    # Test deleting unique attributes
    del unique.attr
    unique.save()
    unique.attr = "test"
    unique.save()
    self.assertEqual("test", unique.attr)

  def test_deleteCollection(self):
    page = ClassPage(name="Some Page")
    u = SomeUser(page=page)
    u.save() # this saves page
    self.assertEqual(u.page.name, "Some Page")

    SomeUser.flushDocumentFromCache(u)
    page.delete()
    user = SomeUser.get(u.key)
    self.assertEqual(user.page, None)

  def test_addLinks(self):
    page1 = ClassPage(name="Page1")
    page2 = ClassPage(name="Page2")
    page1.addLink(page2)
    page2.save()
    page1.save()

    self.assertEqual(1, len(page1.getLinks()))
    self.assertEqual(1, len(page1._obj.get_links()))
    self.assertEqual(page2.key, page1._obj.get_links()[0].get_key())

    page1.reload()

    self.assertEqual(1, len(page1.getLinks()))
    self.assertEqual(1, len(page1._obj.get_links()))
    self.assertEqual(page2.key, page1._obj.get_links()[0].get_key())

  def test_removeLinks(self):
    page1 = ClassPage(name="Page1")
    page2 = ClassPage(name="Page2")
    page1.addLink(page2)
    page2.save()
    page1.save()

    page1.reload()

    page1.removeLink(page2)

    self.assertEqual(0, len(page1.getLinks()))

    page1.save()
    page1.reload()

    self.assertEqual(0, len(page1.getLinks()))


if __name__ == "__main__":
  try:
    import doctest
    print "Running doctests from README.md ..."
    failures, attempts = doctest.testfile("README.md")
    print "Ran through %d tests with %d failures." % (attempts, failures)
    print
    if not failures:
      print "Running unittests..."
      unittest.main()
    else:
      print "Doctest failure, fix those errors first!"
  finally:
    print "Cleaning up..."

    # Clean up
    buckets_to_be_cleaned = ("test_blog", "test_users", "test_comments", "demos",
        "test_website", "coolusers", "_CoolUser_ul_username", "testdoc",
        "test_person", "test_cake", "some_extended_bucket", "test_A", "test_B",
        "test_unique", "_UniqueTest_ul_attr", "test_class", "test_someuser")

    for bucket in buckets_to_be_cleaned:
      deleteAllKeys(rc, bucket)
