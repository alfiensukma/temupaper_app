from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from datetime import datetime

def access_history(request):
    topic = ["AI", "Data Science", "Machine Learning"]
    
    papers = [
        {
            "title": "In silico exploration of the fructose-6-phosphate phosphorylation step in glycolysis: genomic evidence of the coexistence of an atypical ATP-dependent along with a PPi-dependent phosphofructokinase in Propionibacterium freudenreichii subsp. shermanii",
            "authors": ["Alice", "Bob"],
            "date": "2023-10-12",
            "abstract": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Curabitur vitae sem mollis ligula semper ornare eu et sem. Cras sodales dapibus nunc, eu lobortis nunc condimentum ac. Integer quis semper ante, sed suscipit libero. Maecenas consectetur neque a eleifend laoreet. Ut id commodo risus. Mauris porttitor nibh eu turpis dignissim, vitae egestas nibh scelerisque. Vivamus sit amet feugiat lacus. Quisque tincidunt, mi at tincidunt vestibulum, augue lacus interdum justo, id blandit sapien tellus eget enim. Nulla facilisi. Curabitur nisl orci, vehicula eu felis quis, sollicitudin consequat lectus. Morbi convallis nunc eget mi elementum, ac dictum erat eleifend. Donec at lectus consectetur magna porta consequat. In dignissim pellentesque magna, non interdum purus pretium at. Suspendisse eleifend lacus mollis odio varius viverra. Curabitur in imperdiet magna, congue bibendum magna. Vivamus eget dui sodales, auctor neque sed, vehicula arcu. Nunc sed turpis vel sem tempor commodo in at velit. Etiam rhoncus leo at varius varius. Proin eget nunc et nisi suscipit ultricies. Nullam pulvinar, massa nec tempus accumsan, lacus ligula vestibulum eros, facilisis tempor erat magna nec odio. Aenean mattis lectus eu augue interdum fringilla. Aenean sed ullamcorper ligula. Proin vel est feugiat sapien pellentesque suscipit. In blandit, tortor a bibendum bibendum, diam mauris pretium sem, non faucibus augue tortor ac orci. Aliquam vel metus purus. Praesent iaculis libero erat."
        },
        {
            "title": "In silico exploration of the fructose-6-phosphate phosphorylation step in glycolysis: genomic evidence of the coexistence of an atypical ATP-dependent along with a PPi-dependent phosphofructokinase in Propionibacterium freudenreichii subsp. shermanii",
            "authors": ["Alice", "Bob"],
            "date": "2023-10-12",
            "abstract": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Curabitur vitae sem mollis ligula semper ornare eu et sem. Cras sodales dapibus nunc, eu lobortis nunc condimentum ac. Integer quis semper ante, sed suscipit libero. Maecenas consectetur neque a eleifend laoreet. Ut id commodo risus. Mauris porttitor nibh eu turpis dignissim, vitae egestas nibh scelerisque. Vivamus sit amet feugiat lacus. Quisque tincidunt, mi at tincidunt vestibulum, augue lacus interdum justo, id blandit sapien tellus eget enim. Nulla facilisi. Curabitur nisl orci, vehicula eu felis quis, sollicitudin consequat lectus. Morbi convallis nunc eget mi elementum, ac dictum erat eleifend. Donec at lectus consectetur magna porta consequat. In dignissim pellentesque magna, non interdum purus pretium at. Suspendisse eleifend lacus mollis odio varius viverra. Curabitur in imperdiet magna, congue bibendum magna. Vivamus eget dui sodales, auctor neque sed, vehicula arcu. Nunc sed turpis vel sem tempor commodo in at velit. Etiam rhoncus leo at varius varius. Proin eget nunc et nisi suscipit ultricies. Nullam pulvinar, massa nec tempus accumsan, lacus ligula vestibulum eros, facilisis tempor erat magna nec odio. Aenean mattis lectus eu augue interdum fringilla. Aenean sed ullamcorper ligula. Proin vel est feugiat sapien pellentesque suscipit. In blandit, tortor a bibendum bibendum, diam mauris pretium sem, non faucibus augue tortor ac orci. Aliquam vel metus purus. Praesent iaculis libero erat."
        },
        {
            "title": "In silico exploration of the fructose-6-phosphate phosphorylation step in glycolysis: genomic evidence of the coexistence of an atypical ATP-dependent along with a PPi-dependent phosphofructokinase in Propionibacterium freudenreichii subsp. shermanii",
            "authors": ["Alice", "Bob"],
            "date": "2023-10-12",
            "abstract": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Curabitur vitae sem mollis ligula semper ornare eu et sem. Cras sodales dapibus nunc, eu lobortis nunc condimentum ac. Integer quis semper ante, sed suscipit libero. Maecenas consectetur neque a eleifend laoreet. Ut id commodo risus. Mauris porttitor nibh eu turpis dignissim, vitae egestas nibh scelerisque. Vivamus sit amet feugiat lacus. Quisque tincidunt, mi at tincidunt vestibulum, augue lacus interdum justo, id blandit sapien tellus eget enim. Nulla facilisi. Curabitur nisl orci, vehicula eu felis quis, sollicitudin consequat lectus. Morbi convallis nunc eget mi elementum, ac dictum erat eleifend. Donec at lectus consectetur magna porta consequat. In dignissim pellentesque magna, non interdum purus pretium at. Suspendisse eleifend lacus mollis odio varius viverra. Curabitur in imperdiet magna, congue bibendum magna. Vivamus eget dui sodales, auctor neque sed, vehicula arcu. Nunc sed turpis vel sem tempor commodo in at velit. Etiam rhoncus leo at varius varius. Proin eget nunc et nisi suscipit ultricies. Nullam pulvinar, massa nec tempus accumsan, lacus ligula vestibulum eros, facilisis tempor erat magna nec odio. Aenean mattis lectus eu augue interdum fringilla. Aenean sed ullamcorper ligula. Proin vel est feugiat sapien pellentesque suscipit. In blandit, tortor a bibendum bibendum, diam mauris pretium sem, non faucibus augue tortor ac orci. Aliquam vel metus purus. Praesent iaculis libero erat."
        },
        {
            "title": "In silico exploration of the fructose-6-phosphate phosphorylation step in glycolysis: genomic evidence of the coexistence of an atypical ATP-dependent along with a PPi-dependent phosphofructokinase in Propionibacterium freudenreichii subsp. shermanii",
            "authors": ["Alice", "Bob"],
            "date": "2023-10-12",
            "abstract": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Curabitur vitae sem mollis ligula semper ornare eu et sem. Cras sodales dapibus nunc, eu lobortis nunc condimentum ac. Integer quis semper ante, sed suscipit libero. Maecenas consectetur neque a eleifend laoreet. Ut id commodo risus. Mauris porttitor nibh eu turpis dignissim, vitae egestas nibh scelerisque. Vivamus sit amet feugiat lacus. Quisque tincidunt, mi at tincidunt vestibulum, augue lacus interdum justo, id blandit sapien tellus eget enim. Nulla facilisi. Curabitur nisl orci, vehicula eu felis quis, sollicitudin consequat lectus. Morbi convallis nunc eget mi elementum, ac dictum erat eleifend. Donec at lectus consectetur magna porta consequat. In dignissim pellentesque magna, non interdum purus pretium at. Suspendisse eleifend lacus mollis odio varius viverra. Curabitur in imperdiet magna, congue bibendum magna. Vivamus eget dui sodales, auctor neque sed, vehicula arcu. Nunc sed turpis vel sem tempor commodo in at velit. Etiam rhoncus leo at varius varius. Proin eget nunc et nisi suscipit ultricies. Nullam pulvinar, massa nec tempus accumsan, lacus ligula vestibulum eros, facilisis tempor erat magna nec odio. Aenean mattis lectus eu augue interdum fringilla. Aenean sed ullamcorper ligula. Proin vel est feugiat sapien pellentesque suscipit. In blandit, tortor a bibendum bibendum, diam mauris pretium sem, non faucibus augue tortor ac orci. Aliquam vel metus purus. Praesent iaculis libero erat."
        },
    ]

    # Format dates
    for paper in papers:
        try:
            dt = datetime.strptime(paper["date"], "%Y-%m-%d")
            paper["date"] = dt.strftime("%d %B %Y")
        except Exception as e:
            print(f"Date parse error: {e}")

    # Topic-specific papers for the popup
    topic_papers = {
        "AI": [
            {"title": "Advances in Artificial Intelligence"},
            {"title": "AI for Healthcare"}
        ],
        "Data Science": [
            {"title": "Data Science for Business"}
        ],
        "Machine Learning": [
            {"title": "Deep Learning Techniques"}
        ]
    }
    
    history_papers = [
        {
            "id": 1,
            "title": "In silico exploration of the fructose-6-phosphate phosphorylation step in glycolysis",
            "checked": False
        },
        {
            "id": 2,
            "title": "Deep Learning Applications in Modern Healthcare",
            "checked": False
        },
        {
            "id": 3,
            "title": "Advanced Data Science Techniques for Business Analytics",
            "checked": False
        }
    ]

    return render(request, "base.html", {
        "content_template": "access-history-recommendation/index.html",
        "body_class": "bg-gray-100",
        "show_search_form": False,
        "papers": papers,
        "topics": topic,
        "topic_papers": topic_papers,
        "history_papers": history_papers,
    })