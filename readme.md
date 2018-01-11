I have worked with Ansible enough to figure out how to get some basic configuration done. I wanted to document some of these basic approaches to set a baseline. 

Using our vagrant machine and a CSR router we will go through different methods to configure a router.

* copying from cfg file to deploy to the router

* tasks defined in the main playbook

* tasks using roles in three different ways

  * tasks defined in the role
  * tasks that import tasks
  * tasks that use a jinja2 template to populate a config using role-specific vars


I tried to take an example of using ansible with the tools that we use today to configure a new site--a spreadsheet.

I have a spreadsheet that collects the information you would most likely use to configure a router (SNMP, NTP, routing process, interface configuration).

I use a Python script to populate a yml file that then, via jinja2 template, populates a router config. The end result is a standard router config.

``` 
hostname CSR01

ip domain-name example.com
crypto key generate rsa modulus 2048


snmp-server community publicRO



router ospf 100
router-id 1.1.1.1



interface g1
  
  description to_Core
  ip address 192.168.1.1 255.255.255.252
  ip ospf 100 area 0
  no shutdown

interface g2
  
  description to_Core
  ip address 192.168.1.4 255.255.255.252
  ip ospf 100 area 1
  no shutdown

interface lo1
  
  description EIGRP RID
  ip address 1.1.1.1 255.255.255.255
  ip ospf 100 area 0
  no shutdown

```

We can use an ansible playbook to run that python script. We can then use an ansible playbook to apply that config to a router. 

There is a global hosts file that we can use to define hosts or groups of hosts. In this case I am using one local to this playbook directory so I can be more flexible in testing different scenarios. Here is what it looks like.

~~~

localhost ansible_connection=local

[CSR]
172.16.9.155
[CSR:vars]
ansible_connection=local
~~~

I run the playbook and include the hosts file:

~~~
ansible-playbook csr_config.yml -i ./hosts
~~~

Here is what the playbook looks like.

~~~


---
- name: Configure a CSR Router
  hosts: CSR
  vars:
    creds:
      username: admin
      password: cisco
      authorize: yes


  tasks:
    - name: apply config file to the router
      ios_config:
        provider: "{{ creds }}"
        authorize: yes
        src: "/Github/AnsibleNetExamples/CSR-Builder/cfg_files/CSR01.cfg"
        
~~~

*NOTE: Notice we define our credentials right in the playbook. We then reference a provider in our tasks that says to use the credentials. Since Ansible 2.3 we can pass authentication via command line so we don't have to store credentials in our playbooks. You could use vault to store encrypted credentials (that is for another time)*

*We will use the method of passing credentials via command line when we start using roles.*

Next we'll define the router configuration within a single playbook. This playbook simply set an NTP server and sets an IP address and description on an interface. This takes the syntax of the router and defines those items. Notice the parents line. This allows us to put configuration  in interface configuration mode.

~~~

---

- name: Apply Configuration to CSR
  hosts: CSR
  vars:
    creds:
      username: admin
      password: cisco

  tasks:
    - name: Configure Interface G2
      ios_config:
        provider: "{{ creds }}"
        lines:
          - ip address 10.1.1.1 255.255.255.252
          - description Configured by Ansible Playbook CSR-Basic
        parents: interface g1
    - name: Configure NTP
      ios_config:
        provider: "{{ creds }}"
        lines: ntp server 8.8.8.8
        
~~~

We could keep adding tasks to this configuration to make a complete router configuration, but instead we will start to abstract the different areas of configuration to different roles. This comes in handy for static configuration you may have. For example things like NTP servers, or SNMP servers probably don't change as often as switchport configurations or even routing configurations. We can define an NTP role that we can call from another variable. That way we never have to worry about accidentally changing that playbook while we are working on something else. 

Let's look at the directory structure we will need within our ansible directories to take advantage of these abstractions. 

~~~
├── hosts
├── roles
│   ├── interfaces
│   │   ├── Tasks
│   │   │   └── main.yml
│   │   ├── templates
│   │   │   └── int.j2
│   │   └── vars
│   │       └── main.yml
│   ├── ntp
│   │   ├── tasks
│   │   │   └── main.yml
│   │   └── templates
│   └── ospf
│       ├── tasks
│       │   ├── main.yml
│       │   ├── ospf-int.yml
│       │   └── ospf-proc.yml
│       └── templates
└── site.yml
~~~

Our site.yml file does nothing more than say what hosts we want to run the playbook on and what roles we want to run.  Here is the top-level site.yml.

~~~
---

- name: provide creds
  hosts: CSR

  roles:
    - ntp
    - ospf
    - interfaces

~~~
 
 We have roles for ntp, ospf, and interfaces defined.  Notice that each role has its own directory structure. There are more directories we could create, but we are keeping it simple with tasks, templates, and vars.
 
 Here is the main.yml file for the ntp role.
 
~~~
---

- name: set ntp server
  ios_config:
    lines:
      - ntp server 10.1.1.1

~~~
  
It just very simply sets the ntp server. 
  
Next we'll abstract those roles a bit more with the include-tasks functionality. For OSPF we want to set the OSPF process id and router id, we also want to set the interface level command to make it an OSPF interface.

our main.yml for the OSPF role is as follows.

~~~
---

- import_tasks: ospf-proc.yml
- import_tasks: ospf-int.yml
- 
~~~

This role imports its task from two other files in the same directory.
The ospf-proc.yml sets the process-id and RID.

~~~
---

- name: set ospf process
  ios_config:
    lines:
      - router ospf 100

- name: set router id
  ios_config:
    lines:
      - router-id 1.1.1.1
    parents: router ospf 100

~~~

The ospf-int.yml configures the interface.

~~~

---

- name: set OSPF Interface
  ios_config:
    lines:
      - ip ospf 100 area 0
    parents:
      - interface g1
~~~

Lastly, we have the interfaces role. We are going to apply the config from the jinja2 file included in the templates directory.

~~~

---

- name: configure interface settings
  ios_config:
    src: int.j2
    
~~~

Let's look at the jinja2 template. Here we are referencing variables, these variables are in the main.yml file under the vars directory for this role. 

We are creating a loop for each interface defined in the vars file.

~~~
{% for interface in interface.name %}
interface {{ interface['int'] }}
description {{ interface['description'] }}
ip address {{ interface['ip'] }} {{ interface['mask']}}
no shutdown
{% endfor %}

~~~

In this loop we are creating configuration lines for which interface, interface description and an IP address. In our vars, we create dictionary for each interface and reference the dict items within our for loop in the jinja2 template.

~~~
---

interface:
  name: 
    - { int: g2, description: created by ansible, ip: 10.1.1.2, mask: 255.255.255.0}
    - { int: g1, description: created by ansible, ip: 10.2.1.2, mask: 255.255.255.0}

~~~ 

You'll notice we never defined our provider in these examples. We will run the playbook and pass in our username and password on the command line.

~~~

ubuntu@ubuntu-xenial:/Github/AnsibleNetExamples/CSR-Roles$ ansible-playbook -i ./hosts site.yml -u admin -k
SSH password:

PLAY [CSR Roles Playbook] ********************************************************************************************************************

TASK [Gathering Facts] ***********************************************************************************************************************
ok: [172.16.9.155]

TASK [ntp : set ntp server] ******************************************************************************************************************
changed: [172.16.9.155]

TASK [ospf : set ospf process] ***************************************************************************************************************
changed: [172.16.9.155]

TASK [ospf : set router id] ******************************************************************************************************************
changed: [172.16.9.155]

TASK [ospf : set OSPF Interface] *************************************************************************************************************
changed: [172.16.9.155]

TASK [interfaces : configure interface settings] *********************************************************************************************
changed: [172.16.9.155]

PLAY RECAP ***********************************************************************************************************************************
172.16.9.155               : ok=6    changed=5    unreachable=0    failed=0

~~~


*NOTE: I did have some issues with SSH and network devices. I've found that if you edit the /etc/ansible/ansible.cfg file to disable host key checking under defaults and record host keys under the paramiko settings, it works a bit better.*

~~~

# uncomment this to disable SSH key host checking
host_key_checking = False

...

# uncomment this line to cause the paramiko connection plugin to not record new host
# keys encountered.  Increases performance on new host additions.  Setting works independently of the
# host key checking setting above.
record_host_keys=False

~~~