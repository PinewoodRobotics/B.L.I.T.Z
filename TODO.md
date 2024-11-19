# TODO

1. add "retranslating" where basically message with topic "image/process/april/detect" will be first sent to "image/process" and then, when done, the output will be sent to "april/detect"
2. add a "camera" config section that has all the camera parameters in it.
3. timeit does not work with asyncio and nats when passing function with it inside the subscribe callback.
