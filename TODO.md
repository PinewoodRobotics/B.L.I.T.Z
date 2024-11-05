# TODO

1. there is a bunch of dupe code as a result of this system of coding - splitting @all into smaller modules
   1. perhaps make some py code accessible from ALL modules...?
2. add "retranslating" where basically message with topic "image/process/april/detect" will be first sent to "image/process" and then, when done, the output will be sent to "april/detect"
3. possibly NOT decode/encode into/from base64 when sending/receiving images.
   1. put into image and then pass around that file
4. add a "camera" config section that has all the camera parameters in it.
