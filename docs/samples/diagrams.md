---
buttons:
  - title: Documentation
    icon: material-book-outline
    attributes:
      class: md-content__button md-icon
      href: https://squidfunk.github.io/mkdocs-material/reference/diagrams/
      target: _blank
---

# Diagrams

## Mermaid

Check out [Mermaid's documentation](https://mermaid.js.org/intro/) for a reference of all supported diagrams.

### Flowchart

Pellentesque nec lacus est. Phasellus pulvinar volutpat nisl aliquet auctor.  
Nunc tincidunt molestie mi, et porttitor lectus congue in. Aliquam eu tortor viverra libero imperdiet suscipit. 

<center>
```mermaid
flowchart TD
    A[Start] --> B{Is it?}
    B -->|Yes| C[OK]
    C --> D[Rethink]
    D --> B
    B ---->|No| E[End]
```
</center>

Phasellus auctor consectetur diam et ullamcorper. Ut vel lacus massa. Quisque magna magna, semper quis feugiat at, lobortis non leo. Quisque vitae sollicitudin ex. Nulla ut laoreet purus, ut porttitor dui. Suspendisse et ornare erat. Nam id ornare lorem.

Nam quam justo, commodo eu lobortis vestibulum, molestie sed dolor.

<div class="page-break"></div>

### Sequence diagram

Morbi justo enim, rhoncus nec dictum vitae, porttitor ac odio. Pellentesque ac malesuada neque, quis mollis purus.
Aliquam interdum, est a mattis vestibulum, nibh nisl pulvinar orci, a faucibus ante massa et diam.

Phasellus sed velit ex. Proin condimentum dolor ac felis pellentesque imperdiet. Nulla porta est lacus.
Cursus tincidunt cursus diam, sit amet condimentum risus convallis scelerisque.

<center>
```mermaid
sequenceDiagram
    Alice->>John: Hello John, how are you?
    John-->>Alice: Great!
    Alice-)John: See you later!
```
</center>

<div class="page-break"></div>

### Class diagram

Integer iaculis in sem in porttitor. Duis tempus ullamcorper purus, ac efficitur massa aliquam sed. Nam et varius diam. Duis suscipit ultrices odio, non volutpat elit bibendum a. In sit amet ultrices metus. Pellentesque vitae malesuada libero. Phasellus tincidunt cursus diam, sit amet condimentum risus convallis scelerisque. Donec eu luctus tellus, ac porta ex. Nullam dictum eros a consectetur posuere. Donec sed ligula auctor diam faucibus pulvinar nec ut erat. Integer accumsan laoreet mollis. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Aliquam pellentesque tempor pulvinar.

<center>
```mermaid
classDiagram
    note "From Duck till Zebra"
    Animal <|-- Duck
    note for Duck "can fly\ncan swim\ncan dive\ncan help in debugging"
    Animal <|-- Fish
    Animal <|-- Zebra
    Animal : +int age
    Animal : +String gender
    Animal: +isMammal()
    Animal: +mate()
    class Duck{
        +String beakColor
        +swim()
        +quack()
    }
    class Fish{
        -int sizeInFeet
        -canEat()
    }
    class Zebra{
        +bool is_wild
        +run()
    }
```
</center>

Nullam dictum eros a consectetur posuere. Donec sed ligula auctor diam faucibus pulvinar nec ut erat. Integer accumsan laoreet mollis.  
Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Aliquam pellentesque tempor pulvinar.

<div class="page-break"></div>

### Quadrant chart

Duis in consectetur metus, sed vestibulum orci. Quisque tincidunt, nunc eu tincidunt volutpat, risus mi ultricies elit, nec malesuada est ipsum eu lacus. Suspendisse vitae neque pulvinar, tristique lectus sit amet, aliquet arcu. Sed mollis tristique lacus non scelerisque. Suspendisse convallis consequat leo id placerat. Morbi sodales bibendum nibh, vitae interdum erat sagittis sed. Morbi consequat vulputate odio nec mollis. Fusce a neque lacus. Morbi lorem tortor, lobortis id magna imperdiet, malesuada euismod velit.

<center>
```mermaid
quadrantChart
    title Reach and engagement of campaigns
    x-axis Low Reach --> High Reach
    y-axis Low Engagement --> High Engagement
    quadrant-1 We should expand
    quadrant-2 Need to promote
    quadrant-3 Re-evaluate
    quadrant-4 May be improved
    Campaign A: [0.3, 0.6]
    Campaign B: [0.45, 0.23]
    Campaign C: [0.57, 0.69]
    Campaign D: [0.78, 0.34]
    Campaign E: [0.40, 0.34]
    Campaign F: [0.35, 0.78]
```
</center>
