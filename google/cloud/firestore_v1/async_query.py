# Copyright 2020 Google LLC All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Classes for representing queries for the Google Cloud Firestore API.

A :class:`~google.cloud.firestore_v1.query.Query` can be created directly from
a :class:`~google.cloud.firestore_v1.collection.Collection` and that can be
a more common way to create a query than direct usage of the constructor.
"""
from google.cloud.firestore_v1.base_query import (
    BaseQuery,
    _query_response_to_snapshot,
    _collection_group_query_response_to_snapshot,
    _enum_from_direction,
)
from google.cloud.firestore_v1.async_watch import AsyncWatch

from google.cloud.firestore_v1 import _helpers
from google.cloud.firestore_v1 import async_document
from typing import AsyncGenerator


class AsyncQuery(BaseQuery):
    """Represents a query to the Firestore API.

    Instances of this class are considered immutable: all methods that
    would modify an instance instead return a new instance.

    Args:
        parent (:class:`~google.cloud.firestore_v1.collection.CollectionReference`):
            The collection that this query applies to.
        projection (Optional[:class:`google.cloud.proto.firestore.v1.\
            query.StructuredQuery.Projection`]):
            A projection of document fields to limit the query results to.
        field_filters (Optional[Tuple[:class:`google.cloud.proto.firestore.v1.\
            query.StructuredQuery.FieldFilter`, ...]]):
            The filters to be applied in the query.
        orders (Optional[Tuple[:class:`google.cloud.proto.firestore.v1.\
            query.StructuredQuery.Order`, ...]]):
            The "order by" entries to use in the query.
        limit (Optional[int]):
            The maximum number of documents the query is allowed to return.
        offset (Optional[int]):
            The number of results to skip.
        start_at (Optional[Tuple[dict, bool]]):
            Two-tuple of :

            * a mapping of fields. Any field that is present in this mapping
              must also be present in ``orders``
            * an ``after`` flag

            The fields and the flag combine to form a cursor used as
            a starting point in a query result set. If the ``after``
            flag is :data:`True`, the results will start just after any
            documents which have fields matching the cursor, otherwise
            any matching documents will be included in the result set.
            When the query is formed, the document values
            will be used in the order given by ``orders``.
        end_at (Optional[Tuple[dict, bool]]):
            Two-tuple of:

            * a mapping of fields. Any field that is present in this mapping
              must also be present in ``orders``
            * a ``before`` flag

            The fields and the flag combine to form a cursor used as
            an ending point in a query result set. If the ``before``
            flag is :data:`True`, the results will end just before any
            documents which have fields matching the cursor, otherwise
            any matching documents will be included in the result set.
            When the query is formed, the document values
            will be used in the order given by ``orders``.
        all_descendants (Optional[bool]):
            When false, selects only collections that are immediate children
            of the `parent` specified in the containing `RunQueryRequest`.
            When true, selects all descendant collections.
    """

    def __init__(
        self,
        parent,
        projection=None,
        field_filters=(),
        orders=(),
        limit=None,
        limit_to_last=False,
        offset=None,
        start_at=None,
        end_at=None,
        all_descendants=False,
    ) -> None:
        super(AsyncQuery, self).__init__(
            parent=parent,
            projection=projection,
            field_filters=field_filters,
            orders=orders,
            limit=limit,
            limit_to_last=limit_to_last,
            offset=offset,
            start_at=start_at,
            end_at=end_at,
            all_descendants=all_descendants,
        )

    async def get(self, transaction=None) -> list:
        """Read the documents in the collection that match this query.

        This sends a ``RunQuery`` RPC and returns a list of documents
        returned in the stream of ``RunQueryResponse`` messages.

        Args:
            transaction
                (Optional[:class:`~google.cloud.firestore_v1.transaction.Transaction`]):
                An existing transaction that this query will run in.

        If a ``transaction`` is used and it already has write operations
        added, this method cannot be used (i.e. read-after-write is not
        allowed).

        Returns:
            list: The documents in the collection that match this query.
        """
        is_limited_to_last = self._limit_to_last

        if self._limit_to_last:
            # In order to fetch up to `self._limit` results from the end of the
            # query flip the defined ordering on the query to start from the
            # end, retrieving up to `self._limit` results from the backend.
            for order in self._orders:
                order.direction = _enum_from_direction(
                    self.DESCENDING
                    if order.direction == self.ASCENDING
                    else self.ASCENDING
                )
            self._limit_to_last = False

        result = self.stream(transaction=transaction)
        result = [d async for d in result]
        if is_limited_to_last:
            result = list(reversed(result))

        return result

    async def stream(
        self, transaction=None
    ) -> AsyncGenerator[async_document.DocumentSnapshot, None]:
        """Read the documents in the collection that match this query.

        This sends a ``RunQuery`` RPC and then returns an iterator which
        consumes each document returned in the stream of ``RunQueryResponse``
        messages.

        .. note::

           The underlying stream of responses will time out after
           the ``max_rpc_timeout_millis`` value set in the GAPIC
           client configuration for the ``RunQuery`` API.  Snapshots
           not consumed from the iterator before that point will be lost.

        If a ``transaction`` is used and it already has write operations
        added, this method cannot be used (i.e. read-after-write is not
        allowed).

        Args:
            transaction
                (Optional[:class:`~google.cloud.firestore_v1.transaction.Transaction`]):
                An existing transaction that this query will run in.

        Yields:
            :class:`~google.cloud.firestore_v1.async_document.DocumentSnapshot`:
            The next document that fulfills the query.
        """
        if self._limit_to_last:
            raise ValueError(
                "Query results for queries that include limit_to_last() "
                "constraints cannot be streamed. Use Query.get() instead."
            )

        parent_path, expected_prefix = self._parent._parent_info()
        response_iterator = await self._client._firestore_api.run_query(
            request={
                "parent": parent_path,
                "structured_query": self._to_protobuf(),
                "transaction": _helpers.get_transaction_id(transaction),
            },
            metadata=self._client._rpc_metadata,
        )

        async for response in response_iterator:
            if self._all_descendants:
                snapshot = _collection_group_query_response_to_snapshot(
                    response, self._parent
                )
            else:
                snapshot = _query_response_to_snapshot(
                    response, self._parent, expected_prefix
                )
            if snapshot is not None:
                yield snapshot

    def on_snapshot(self, callback) -> AsyncWatch:
        """Monitor the documents in this collection that match this query.

        This starts a watch on this query using a background thread. The
        provided callback is run on the snapshot of the documents.

        Args:
            callback(Callable[[:class:`~google.cloud.firestore.query.QuerySnapshot`], NoneType]):
                a callback to run when a change occurs.

        Example:

        .. code-block:: python

            from google.cloud import firestore_v1

            db = firestore_v1.AsyncClient()
            query_ref = db.collection(u'users').where("user", "==", u'Ada')

            def on_snapshot(docs, changes, read_time):
                for doc in docs:
                    print(u'{} => {}'.format(doc.id, doc.to_dict()))

            # Watch this query
            query_watch = query_ref.on_snapshot(on_snapshot)

            # Terminate this watch
            query_watch.unsubscribe()
        """
        return AsyncWatch.for_query(
            self,
            callback,
            async_document.DocumentSnapshot,
            async_document.AsyncDocumentReference,
        )
