StorPool ansible deployment
===========================

This contains an example role - storpool-common - and an example inventory
file that has the variables which contains the variables that control the
deployment.

This is still work in progress, but is able to do most deployments. Work
is needed for:

- better disk initialization
- tests of CPU settings (turbocheck)
- deployment of integrations (lvmsp, cloudstack)

Workflow for internal users
---------------------------


* Create a branch for yourself:

```
git checkout -b meow
```

* Do your changes, commit them, do, commit, etc;
* Get the latest master in your repo and in your branch:

```
git pull -r origin master
```

* Submit your branch:

```
git push origin meow
```

* If it's acceptable, merge that into master and push:

```
git checkout master
git pull origin meow
git push origin master
```
