- implement Eigen instead of a custom vector3 class
1) the issue is basically that Eigen refuses to compile on my docker machine
- check the time it takes per query and might need to adjust the json writing method
- possibly migrate to use the protobuf format instead of json to optimize the writing of many many points