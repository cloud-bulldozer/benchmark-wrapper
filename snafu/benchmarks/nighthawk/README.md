# Steps to generate nighthawk-base image

1. Create a ubuntu based pod using the below yaml
    ```
    apiVersion: apps/v1
    kind: Deployment
    metadata:
    labels:
        app: http-scale-client-test
    name: http-scale-client-test
    spec:
    replicas: 1
    selector:
        matchLabels:
        app: http-scale-client-test
    template:
        metadata:
        labels:
            app: http-scale-client-test
        spec:
        imagePullPolicy: Always
        hostNetwork: true
        tolerations:
        - effect: NoSchedule
            key: role
            operator: Equal
            value: workload
        containers:
        - name: ubuntu
            image: ubuntu
            command:
            - sleep
            - inf
    ```
2. Login to the host using ```oc rsh http-scale-client-test-[ID] /bin/bash```
3. And follow the installation steps here: https://github.com/envoyproxy/nighthawk#building-on-ubuntu
4. Once the binaries are generated copy them to your local file system using `oc cp` command.
5. Create a Dockerfile in the directory which contains binaries and add the following code snippet.

    ```
    FROM ubuntu
    LABEL description="This is custom image that contains nighthawk executables"
    ENV LogLevel "info"
    COPY * /usr/bin/
    ```
6. Now build the docker file and save the image to your desired image repository.
