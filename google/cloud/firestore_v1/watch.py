# Copyright 2017 Google LLC All rights reserved.
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

import threading

from google.cloud.firestore_v1.types import firestore

from google.cloud.firestore_v1.base_watch import (
    WATCH_TARGET_ID,
    _RPC_ERROR_THREAD_NAME,
    _should_recover,
    _should_terminate,
    _maybe_wrap_exception,
    document_watch_comparator,
    WatchDocTree,
    WatchResult,
    ChangeType,
    DocumentChange,
    BaseWatch,
)

"""Python client for Google Cloud Firestore Watch."""


class Watch(BaseWatch):
    def __init__(
        self,
        document_reference,
        firestore,
        target,
        comparator,
        snapshot_callback,
        document_snapshot_cls,
        document_reference_cls,
        BackgroundConsumer=None,  # FBO unit testing
        ResumableBidiRpc=None,  # FBO unit testing
    ):
        """
        Args:
            firestore:
            target:
            comparator:
            snapshot_callback: Callback method to process snapshots.
                Args:
                    docs (List(DocumentSnapshot)): A callback that returns the
                        ordered list of documents stored in this snapshot.
                    changes (List(str)): A callback that returns the list of
                        changed documents since the last snapshot delivered for
                        this watch.
                    read_time (string): The ISO 8601 time at which this
                        snapshot was obtained.

            document_snapshot_cls: instance of DocumentSnapshot
            document_reference_cls: instance of DocumentReference
        """
        super(Watch, self).__init__(
            document_reference,
            firestore,
            target,
            comparator,
            snapshot_callback,
            document_snapshot_cls,
            document_reference_cls,
            BackgroundConsumer=BackgroundConsumer,
            ResumableBidiRpc=ResumableBidiRpc,
        )
